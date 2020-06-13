import sys
from kubernetes import client, config, watch
import logging
from time import sleep

from types import SimpleNamespace
import datetime
import pytz

from mozalert.state import State, Status
from mozalert.base import BaseCheck

# kubernetes.client.rest.ApiException


class Check(BaseCheck):
    """
    the Check object handles the entire lifecycle of a check:
    * maintains the check interval using threading.Timer (BaseCheck)
    * manages the resources for running the check itself
    * reports status to the CRD object
    * handles escalation
    """

    def __init__(self, **kwargs):
        self.client = kwargs.get("client", client.BatchV1Api())
        self.pod_client = kwargs.get("pod_client", client.CoreV1Api())
        self.crd_client = kwargs.get("crd_client", client.CustomObjectsApi())

        super().__init__(**kwargs)

        self._spec = kwargs.get("spec",{})

    def run_job(self):
        """
        Build the k8s resources, apply them, then poll for completion, and
        report status back to the thread.
        
        The k8s resources take the form:
            pod spec -> pod template -> job spec -> job

        """
        logging.info(f"Running job for {self._namespace}/{self._name}")
        pod_spec = client.V1PodSpec(**self._spec)
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": self._name}), spec=pod_spec
        )
        job_spec = client.V1JobSpec(template=template, backoff_limit=0)
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self._name),
            spec=job_spec,
        )
        try:
            res = self.client.create_namespaced_job(body=job, namespace=self._namespace)
            logging.info(f"Job created for {self._namespace}/{self._name}")
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)

        self._state = State.RUNNING
        self.set_crd_status()

        # wait for the job to finish
        while True:
            status = self.get_job_status()
            if status.active and self._state != State.RUNNING:
                self._state = State.RUNNING
                logging.info("Setting the state to RUNNING")
            if status.start_time:
                self._runtime = datetime.datetime.now() - status.start_time.replace(
                    tzinfo=None
                )
            if status.succeeded:
                logging.info("Setting the job status to OK")
                self._status = Status.OK
                self._state = State.IDLE
            elif status.failed:
                logging.info("Setting the job status to CRITICAL")
                self._status = Status.CRITICAL
                self._state = State.IDLE

            if self._status != Status.PENDING and self._state != State.RUNNING:
                for log_line in self.get_job_logs().split("\n"):
                    logging.info(log_line)
                break
            sleep(self._job_poll_interval)
        logging.info(
            f"Job finished for {self._namespace}/{self._name} in {self._runtime} seconds with status {self._status}"
        )
        self._state = State.IDLE
        self._last_check = str(pytz.utc.localize(datetime.datetime.utcnow()))
        self.set_crd_status()

    def get_job_logs(self):
        """
        since the CRD deletes the pod after its done running, it is nice
        to have a way to save the logs before deleting it. this retrieves
        the pod logs so they can be blasted into the controller logs.
        """
        res = self.pod_client.list_namespaced_pod(
            namespace=self._namespace, label_selector=f"app={self._name}"
        )
        logs = ""
        for pod in res.items:
            logs += self.pod_client.read_namespaced_pod_log(
                pod.metadata.name, self._namespace
            )
        return logs

    def get_job_status(self):
        """
        read the status of the job object and return a SimpleNamespace
        """

        status = SimpleNamespace(
            active=False, succeeded=False, failed=False, start_time=None
        )

        try:
            res = self.client.read_namespaced_job_status(self._name, self._namespace)
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)
            return status

        if res.status.active == 1:
            status.active = True

        if res.status.succeeded:
            status.succeeded = True

        if res.status.failed:
            status.failed = True

        if res.status.start_time:
            status.start_time = res.status.start_time

        return status

    def set_crd_status(self):
        """
        Patch the status subresource of the check object in k8s to use the latest
        status. NOTE: In what I've read in the docs, this should NOT cause a modify
        event, however it does, even when hitting the apiserver directly. We are careful
        to account for this but TODO to understand this further.
        """
        logging.debug(f"Setting CRD status for {self._namespace}/{self._name}")

        status = {
            "status": {
                "status": str(self._status.name),
                "state": str(self._state.name),
                "attempt": str(self._attempt),
                "lastCheckTimestamp": self._last_check,
                "nextCheckTimestamp": self._next_check,
            }
        }

        try:
            res = self.crd_client.patch_namespaced_custom_object_status(
                "crd.k8s.afrank.local",
                "v1",
                self._namespace,
                "checks",
                self._name,
                body=status,
            )
        except Exception as e:
            # failed to set the status
            # TODO should take more action here
            logging.info(sys.exc_info()[0])
            logging.info(e)

    def delete_job(self):
        """
        after a check is complete delete the job which executed it
        """
        try:
            res = self.client.delete_namespaced_job(
                self._name, self._namespace, propagation_policy="Foreground"
            )
        except Exception as e:
            # failure is probably ok here, if the job doesn't exist
            logging.debug(sys.exc_info()[0])
            logging.debug(e)
