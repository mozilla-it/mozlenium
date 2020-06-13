import sys
from kubernetes import client, config, watch
import logging
import threading
from time import sleep

# from types import SimpleNamespace
import datetime
import pytz

from mozalert.state import State, Status

# kubernetes.client.rest.ApiException


class Check:
    def __init__(self, **kwargs):
        """
        initialize/reinitialize a check
        """
        self._name = kwargs.get("name")
        self._namespace = kwargs.get("namespace")
        self._spec = kwargs.get("spec")
        self._check_interval = float(kwargs.get("check_interval"))
        self._retry_interval = float(kwargs.get("retry_interval", 0))
        self._notification_interval = float(kwargs.get("notification_interval", 0))
        self._job_poll_interval = float(kwargs.get("job_poll_interval", 3))

        self._max_attempts = int(kwargs.get("max_attempts", "3"))

        self.client = kwargs.get("client", client.BatchV1Api())
        self.pod_client = kwargs.get("pod_client", client.CoreV1Api())
        self.crd_client = kwargs.get("crd_client", client.CustomObjectsApi())

        self._update = kwargs.get("update", False)

        if not self._retry_interval:
            self._retry_interval = self._check_interval
        if not self._notification_interval:
            self._notification_interval = self._check_interval

        """
        initialize the check for the first time
        """
        if not self._update:
            self._shutdown = False
            self._attempt = 0
            self._runtime = 0
            self._last_check = None
            self._next_check = None

            self._status = Status.PENDING
            self._state = State.IDLE

            self.thread = None

            self._next_interval = self._check_interval

            self.start_thread()
            self.set_crd_status()

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace

    @property
    def spec(self):
        return self._spec

    def __repr__(self):
        return f"{self._namespace}/{self._name}"

    def update(self, **kwargs):
        """
        When the object is modified call this to modify the running check instance
        """
        self.__init__(**kwargs, update=True)

    def shutdown(self):
        self._shutdown = True
        try:
            self.stop_thread()
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)

        self.delete_job()

    def check(self):
        """
        main thread for creating then watching a check job; this is called by 
        the Timer thread.
        """
        logging.info(
            f"Running the check thread instance for {self._namespace}/{self._name}"
        )
        self._attempt += 1
        self.run_job()
        logging.info(f"Check finished for {self._namespace}/{self._name}")
        logging.debug(f"Cleaning up finished job for {self._namespace}/{self._name}")
        self.delete_job()
        if self._status == Status.OK:
            # check passed, things are great!
            self._attempt = 0
            self._next_inteval = self._check_interval
        elif self._attempt >= self._max_attempts:
            # state is not OK and we've run out of attempts. do the escalation
            logging.info("Escalating {self._namespace}/{self._name}")
            self._next_interval = self._retry_interval
            # ^ TODO keep retrying after escalation? giveup? reset?
        else:
            # not state OK and not enough failures to escalate
            self._next_interval = self._retry_interval

        # set the next_check for the CRD status
        self._next_check = str(
            pytz.utc.localize(datetime.datetime.utcnow())
            + datetime.timedelta(minutes=self._next_interval)
        )
        if not self._shutdown:
            # officially schedule the next run
            self.start_thread()
            # update the CRD status subresource
            self.set_crd_status()

    def start_thread(self):
        logging.debug(
            f"Starting check thread for {self._namespace}/{self._name} at interval {self._next_interval}"
        )

        self.thread = threading.Timer(self._next_interval * 60, self.check)
        self.thread.setName(f"{self._namespace}/{self._name}")
        self.thread.start()

        self._next_check = str(
            pytz.utc.localize(datetime.datetime.utcnow())
            + datetime.timedelta(minutes=self._next_interval)
        )

    def stop_thread(self):
        logging.debug(f"Stopping check thread for {self._namespace}/{self._name}")
        if self.thread:
            self.thread.cancel()
            self.thread.join()

    def run_job(self):
        """
        Build the k8s resources, apply them, then poll for completion, and
        report status back to the thread.
        
        The k8s resources take the form:
            pod spec -> pod template -> job spec -> job

        """
        logging.debug(f"Running job for {self._namespace}/{self._name}")
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
            api_response = self.client.create_namespaced_job(
                body=job, namespace=self._namespace
            )
            logging.info(f"Job created for {self._namespace}/{self._name}")
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)

        self._state = State.RUNNING
        self.set_crd_status()

        # wait for the job to finish
        while True:
            self.set_thread_status()
            if self._status != Status.PENDING and self._state != State.RUNNING:
                logging.info(self._status)
                logging.info(self._state)
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
        api_response = self.pod_client.list_namespaced_pod(
            namespace=self._namespace, label_selector=f"app={self._name}"
        )
        logs = ""
        for pod in api_response.items:
            logs += self.pod_client.read_namespaced_pod_log(
                pod.metadata.name, self._namespace
            )
        return logs

    def set_thread_status(self):
        """
        read the status of the job object and set it for the check thread
        """
        try:
            api_response = self.client.read_namespaced_job_status(
                self._name, self._namespace
            )
            if api_response.status.active == 1 and self._state != State.RUNNING:
                self._state = State.RUNNING
                logging.info("Setting the status to RUNNING")
            if api_response.status.start_time:
                self._runtime = datetime.datetime.now() - api_response.status.start_time.replace(
                    tzinfo=None
                )
            if api_response.status.succeeded:
                logging.info("Setting the job state to OK")
                self._status = Status.OK
                self._state = State.IDLE
            elif api_response.status.failed:
                logging.info("Setting the job state to CRITICAL")
                self._status = Status.CRITICAL
                self._state = State.IDLE
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)

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
            api_response = self.client.delete_namespaced_job(
                self._name, self._namespace, propagation_policy="Foreground"
            )
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)
