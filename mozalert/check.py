import os
import sys
from kubernetes import client, config, watch
import logging
from time import sleep

from types import SimpleNamespace
import datetime
import pytz

from mozalert.status import EnumStatus, EnumState, Status
from mozalert.base import BaseCheck

import importlib

from kubernetes.client.rest import ApiException


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

        self._config.spec = kwargs.get("spec", {})

    def escalate(self, recovery=False):
        self.escalated = not recovery
        for esc in self.config.escalations:
            escalation_type = esc.get("type", "email")
            logging.info(f"Escalating {self} via {escalation_type}")
            args = esc.get("args", {})
            try:
                module = importlib.import_module(
                    f".escalations.{escalation_type}", "mozalert"
                )
                Escalation = getattr(module, "Escalation")
                e = Escalation(
                    f"{self}",
                    self.status.status.name,
                    attempt=self.status.attempt,
                    max_attempts=self.config.max_attempts,
                    last_check=str(self.status.last_check),
                    logs=self.status.logs,
                    args=args,
                )
                e.run()
            except Exception as e:
                logging.error(
                    f"Failed to send escalation type {escalation_type} for {self}"
                )
                logging.error(sys.exc_info()[0])
                logging.error(e)

    def run_job(self):
        """
        Build the k8s resources, apply them, then poll for completion, and
        report status back to the thread.
        
        The k8s resources take the form:
            pod spec -> pod template -> job spec -> job

        """
        logging.debug(f"Running job")
        pod_spec = client.V1PodSpec(**self.config.spec)
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": self.config.name}),
            spec=pod_spec,
        )
        job_spec = client.V1JobSpec(template=template, backoff_limit=0)
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self.config.name),
            spec=job_spec,
        )
        logging.debug(f"Creating job")
        # TODO refactor this
        tries = 0
        max_tries = 100
        while tries < max_tries:
            try:
                res = self.client.create_namespaced_job(
                    body=job, namespace=self.config.namespace
                )
                logging.debug(f"Job created")
                break
            except ApiException as e:
                if e.reason == "Conflict":
                    logging.debug(
                        "Found another job already running. Deleting that job"
                    )
                    self.delete_job()
                    tries += 1
                    sleep(self._job_poll_interval)
                else:
                    logging.info(e.reason)
                    raise

        if tries >= max_tries:
            raise Exception(
                f"Max attempts to start the job ({tries}/{max_tries}) exceeded"
            )

        self.status.state = EnumState.RUNNING
        self.set_crd_status()

        # wait for the job to finish
        while True:
            status = self.get_job_status()
            if status.active and not self.status.RUNNING:
                self.status.state = EnumState.RUNNING
            if status.start_time:
                self._runtime = datetime.datetime.utcnow() - status.start_time.replace(
                    tzinfo=None
                )
            if status.succeeded:
                self.status.status = EnumStatus.OK
                self.status.state = EnumState.IDLE
            elif status.failed:
                self.status.status = EnumStatus.CRITICAL
                self.status.state = EnumState.IDLE
            # job is done running so get its logs
            if not self.status.PENDING and not self.status.RUNNING:
                self.get_job_logs()
                for log_line in self.status.logs.split("\n"):
                    logging.debug(log_line)
                break
            if self.config.timeout and self._runtime.seconds > self.config.timeout:
                logging.info("Job Timeout triggered")
                self.status.status = EnumStatus.CRITICAL
                self.status.state = EnumState.IDLE
                self.status.last_check = pytz.utc.localize(datetime.datetime.utcnow())
                self.set_crd_status()
                raise Exception("Job Timeout")
            sleep(self._job_poll_interval)
        logging.info(
            f"Job finished in {self._runtime.seconds} seconds with status {self.status.status.name}"
        )
        self.status.state = EnumState.IDLE
        self.status.last_check = pytz.utc.localize(datetime.datetime.utcnow())
        self.set_crd_status()

    def get_job_logs(self):
        """
        since the CRD deletes the pod after its done running, it is nice
        to have a way to save the logs before deleting it. this retrieves
        the pod logs so they can be blasted into the controller logs.
        """
        try:
            res = self.pod_client.list_namespaced_pod(
                namespace=self.config.namespace,
                label_selector=f"app={self.config.name}",
            )
        except Exception as e:
            logging.debug(sys.exc_info()[0])
            logging.debug(e)
            self.status.logs = ""
            return

        logs = ""
        for pod in res.items:
            logs += self.pod_client.read_namespaced_pod_log(
                pod.metadata.name, self.config.namespace
            )
        self.status.logs = logs

    def get_job_status(self):
        """
        read the status of the job object and return a SimpleNamespace
        """

        status = SimpleNamespace(
            active=False, succeeded=False, failed=False, start_time=None
        )

        try:
            res = self.client.read_namespaced_job_status(
                self.config.name, self.config.namespace
            )
        except Exception as e:
            logging.debug(sys.exc_info()[0])
            logging.info(e.reason)
            status.failed = True
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
        logging.debug(f"Setting CRD status")

        status = {
            "status": {
                "status": str(self.status.status.name),
                "state": str(self.status.state.name),
                "attempt": str(self.status.attempt),
                "lastCheckTimestamp": str(self.status.last_check).split(".")[0],
                "nextCheckTimestamp": str(self.status.next_check).split(".")[0],
                "logs": self.status.logs,
            }
        }

        try:
            res = self.crd_client.patch_namespaced_custom_object_status(
                "crd.k8s.afrank.local",
                "v1",
                self.config.namespace,
                "checks",
                self.config.name,
                body=status,
            )
        except Exception as e:
            # failed to set the status
            # TODO should take more action here
            logging.debug(sys.exc_info()[0])
            logging.debug(e)

    def delete_job(self):
        """
        after a check is complete delete the job which executed it
        """
        logging.debug(f"deleting job")
        try:
            res = self.client.delete_namespaced_job(
                self.config.name,
                self.config.namespace,
                propagation_policy="Foreground",
                grace_period_seconds=0,
            )
        except ApiException as e:
            # failure is probably ok here, if the job doesn't exist
            logging.debug(sys.exc_info()[0])
            logging.debug(e)
