import sys
import logging
from time import sleep

from types import SimpleNamespace

from mozalert import base, status, metrics
from mozalert.utils.dt import now

from mozalert.kubeclient import ApiException

from datetime import timedelta


class Check(base.BaseCheck, metrics.mixin.MetricsMixin):
    """
    the Check object handles the entire lifecycle of a check:
    * maintains the check interval using threading.Timer (BaseCheck)
    * manages the resources for running the check itself
    * reports status to the CRD object
    * handles escalation
    """

    def __init__(self, **kwargs):
        self.kube = kwargs.get("kube")
        self._job_poll_interval = float(kwargs.get("job_poll_interval", 3))
        self._shutdown_max_wait_sec = float(kwargs.get("shutdown_max_wait_sec", 10))

        super().__init__(**kwargs)

    def run_job(self, shutdown=lambda: False):
        """
        Build the k8s resources, apply them, then poll for completion, and
        report status back to the thread.
        
        The k8s resources take the form:
            pod spec -> pod template -> job spec -> job

        """
        logging.debug(f"Running job")

        job = self.kube.make_job(self.config.name, **self.config.pod_spec)

        try:
            res = self.kube.BatchV1Api.create_namespaced_job(
                body=job, namespace=self.config.namespace
            )
            logging.debug(f"Job created")
        except ApiException as e:
            logging.debug(e)
            logging.debug(sys.exc_info()[0])
            # if the job is already there we just
            # move on.
            if e.reason != "Conflict":
                raise

        self.status.state = status.EnumState.RUNNING
        self.set_crd_status()

        # wait for the job to finish
        shutdown_timer = 0
        while True:
            sleep(self._job_poll_interval)
            st = self.get_job_status()

            if shutdown():
                shutdown_timer += self._job_poll_interval

            if st.start_time:
                self._runtime = now() - st.start_time
            else:
                self._runtime += timedelta(seconds=self._job_poll_interval)

            if st.succeeded:
                self.status.status = status.EnumStatus.OK
                self.status.state = status.EnumState.IDLE
            elif st.failed:
                self.status.status = status.EnumStatus.CRITICAL
                self.status.state = status.EnumState.IDLE

            if (
                self.config.timeout and self._runtime.seconds > self.config.timeout
            ) or shutdown_timer >= self._shutdown_max_wait_sec:
                logging.error("Job Timeout triggered")
                self.status.state = status.EnumState.IDLE
                self.status.status = status.EnumStatus.CRITICAL

            if not self.status.PENDING and not self.status.RUNNING:
                break

        logging.info(
            f"Job finished in {self._runtime.seconds} seconds with status {self.status.status.name}"
        )

        self.get_job_logs()

        self.status.state = status.EnumState.IDLE
        self.status.last_check = now()
        self.set_crd_status()

    def get_job_logs(self):
        """
        since the CRD deletes the pod after its done running, it is nice
        to have a way to save the logs before deleting it. this retrieves
        the pod logs so they can be blasted into the controller logs.
        """
        try:
            res = self.kube.CoreV1Api.list_namespaced_pod(
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
            logs += self.kube.CoreV1Api.read_namespaced_pod_log(
                pod.metadata.name, self.config.namespace
            )
        logs, telemetry = self.extract_telemetry_from_logs(logs)
        if telemetry:
            logging.debug(f"Found telemetry: {telemetry}")
            self.status.telemetry = telemetry
        self.status.logs = logs

    def get_job_status(self):
        """
        read the status of the job object and return a SimpleNamespace
        """

        status = SimpleNamespace(
            active=False, succeeded=False, failed=False, start_time=None
        )

        try:
            res = self.kube.BatchV1Api.read_namespaced_job_status(
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

        try:
            res = self.kube.CustomObjectsApi.patch_namespaced_custom_object_status(
                "crd.k8s.afrank.local",
                "v1",
                self.config.namespace,
                "checks",
                self.config.name,
                body=self.status.crd_status,
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
            res = self.kube.BatchV1Api.delete_namespaced_job(
                self.config.name,
                self.config.namespace,
                propagation_policy="Foreground",
                grace_period_seconds=0,
            )
        except Exception as e:
            # failure is probably ok here, if the job doesn't exist
            logging.debug(sys.exc_info()[0])
            logging.debug(e)

