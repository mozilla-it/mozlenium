from kubernetes import client, config, watch
import os
import logging
import threading
import queue
from time import sleep

from mozalert.check import Check
from mozalert.metrics import MetricsThread

import re
from datetime import timedelta


class Controller:
    """
    the Controller runs the main thread which tails the event stream for objects in our CRD. It
    manages check threads and ensures they run when/how they're supposed to.
    """

    def __init__(self, **kwargs):
        self._domain = kwargs.get("domain", "crd.k8s.afrank.local")
        self._version = kwargs.get("version", "v1")
        self._plural = kwargs.get("plural", "checks")
        self._check_cluster_interval = kwargs.get("check_cluster_interval", 60)

        self.metrics_queue = queue.Queue()

        if "KUBERNETES_PORT" in os.environ:
            config.load_incluster_config()
        else:
            config.load_kube_config()

        self._client_config = client.Configuration()
        self._client_config.assert_hostname = False

        self._api_client = client.api_client.ApiClient(
            configuration=self._client_config
        )
        self._clients = {
            "client": client.BatchV1Api(),
            "pod_client": client.CoreV1Api(),
            "crd_client": client.CustomObjectsApi(self._api_client),
        }

        self._threads = {}

    @property
    def threads(self):
        return self._threads

    @property
    def clients(self):
        return self._clients

    @property
    def domain(self):
        return self._domain

    @property
    def version(self):
        return self._version

    @property
    def plural(self):
        return self._plural

    @staticmethod
    def build_spec(name, image, **kwargs):
        secret_ref = kwargs.get("secret_ref", None)
        check_cm = kwargs.get("check_cm", None)
        check_url = kwargs.get("check_url", None)
        args = kwargs.get("args", [])
        template = {
            "restart_policy": "Never",
            "containers": [{"name": name, "image": image}],
        }
        if secret_ref:
            template["containers"][0]["envFrom"] = [{"secretRef": {"name": secret_ref}}]
        if check_cm:
            template["containers"][0]["volumeMounts"] = [
                {"name": "checks", "mountPath": "/checks", "readOnly": True}
            ]
            template["volumes"] = [{"name": "checks", "configMap": {"name": check_cm}}]
        if check_url:
            template["containers"][0]["args"] = [check_url]
        elif args:
            template["containers"][0]["args"] = args
        return template

    @staticmethod
    def parse_time(time_str):
        """
        parse_time takes either a number (in minutes) or a formatted time string [XXh][XXm][XXs]
        """
        try:
            minutes = float(time_str)
            return timedelta(minutes=minutes)
        except:
            # didn't pass a number, move on to parse the string
            pass
        regex = re.compile(
            r"((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?"
        )
        parts = regex.match(time_str)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in iter(parts.items()):
            if param:
                time_params[name] = int(param)
        return timedelta(**time_params)

    def check_cluster(self):
        """
        a thread which runs periodically and provides a sanity check that things are working
        as they should. When the check is done, it sends a message to a passive monitor so
        we know the check has run successfully.

        We perform the following actions:
        * check the status of each thread in the self.threads list
        * make sure all next_check's are in the future
        * checks haven't been in running state too long
        * compare the k8s state to the running cluster state
        * send cluster telemetry to prometheus
        * send cluster telemetry to deadmanssnitch
        """
        logging.info("Checking Cluster Status")

        checks = {}
        check_list = self.clients["crd_client"].list_cluster_custom_object(
            self.domain, self.version, self.plural, watch=False
        )

        for obj in check_list.get("items"):
            name = obj["metadata"]["name"]
            namespace = obj["metadata"]["namespace"]
            tname = f"{namespace}/{name}"
            checks[tname] = obj

        for tname in checks.keys():
            if tname not in self.threads:
                logging.info(f"thread {tname} not found in self.threads")
            check_status = checks[tname].get("status")
            thread_status = self.threads[tname].status
            if (
                int(check_status.get("attempt")) != thread_status.attempt
                or check_status.get("state") != thread_status.state.name
                or check_status.get("status") != thread_status.status.name
            ):
                logging.info("Check status does not match thread status!")
                logging.info(check_status)
                logging.info(
                    f"{thread_status.status.name} {thread_status.state.name} {thread_status.attempt}"
                )

        for tname in self.threads:
            if str(tname) not in checks:
                logging.info(f"{tname} not found in server-side checks")

        self.start_cluster_monitor()

    def start_cluster_monitor(self):
        """
        Handle the check_cluster thread
        """

        logging.info(
            f"Starting cluster monitor thread at interval {self._check_cluster_interval}"
        )
        self._check_thread = threading.Timer(
            self._check_cluster_interval, self.check_cluster
        )
        self._check_thread.setName("cluster-monitor")
        self._check_thread.start()

    def run(self):
        """
        the main thread watches the api server event stream for our crd objects and process
        events as they come in. Each event has an associated operation:
        
        ADDED: a new check has been created. the main thread creates a new check object which
               creates a threading.Timer set to the check_interval.
        
        DELETED: a check has been removed. Cancel/resolve any running threads and delete the
                 check object.

        MODIFIED: this can be triggered by the user patching their check, or by a check thread
                  updating the object status. NOTE: updating the status subresource SHOULD NOT
                  trigger a modify, this is probably a bug in k8s. when a check is updated the
                  changes are applied to the check object.

        ERROR: this can occur sometimes when the CRD is changed; it causes the process to die
               and restart.

        """

        self.start_cluster_monitor()

        self.metrics_thread = MetricsThread(q=self.metrics_queue)
        self.metrics_thread.setName("metrics-thread")
        self.metrics_thread.start()

        logging.info("Waiting for events...")
        resource_version = ""
        while True:
            stream = watch.Watch().stream(
                self.clients["crd_client"].list_cluster_custom_object,
                self.domain,
                self.version,
                self.plural,
                resource_version=resource_version,
            )
            for event in stream:
                obj = event.get("object")
                operation = event.get("type")
                # restart the controller if ERROR operation is detected.
                # dying is harsh but in theory states should be preserved in the k8s object.
                # I've only seen the ERROR state when applying changes to the CRD definition
                # and in those cases restarting the controller pod is appropriate. TODO validate
                if operation == "ERROR":
                    logging.error("Received ERROR operation, Dying.")
                    return 2
                if operation not in ["ADDED", "MODIFIED", "DELETED"]:
                    logging.warning(
                        f"Received unexpected operation {operation}. Moving on."
                    )
                    continue

                spec = obj.get("spec")
                status = obj.get("status", {})
                intervals = {
                    "check_interval": self.parse_time(
                        spec.get("check_interval")
                    ).seconds,
                    "retry_interval": self.parse_time(
                        spec.get("retry_interval", "")
                    ).seconds,
                    "notification_interval": self.parse_time(
                        spec.get("notification_interval", "")
                    ).seconds,
                }
                max_attempts = spec.get("max_attempts", 3)
                timeout = self.parse_time(
                    spec.get("timeout", "5m")
                ).seconds  # TODO consider parameterizing some cluster defaults

                escalations = spec.get("escalations", [])

                metadata = obj.get("metadata")
                name = metadata.get("name")
                namespace = metadata.get("namespace")
                thread_name = f"{namespace}/{name}"

                # when we restart the stream start from events after this version
                resource_version = metadata.get("resourceVersion")

                # you can define the pod template either by specifying the entire
                # template, or specifying the values necessary to generate one:
                # image: the check image to run
                # secretRef: where you store secrets to be passed to your chec
                #            as env vars
                # check_cm: the configMap containing the body of your check
                pod_spec = spec.get("podSpec", {})
                if not pod_spec:
                    pod_spec = self.build_spec(
                        name=name,
                        image=spec.get("image", None),
                        secret_ref=spec.get("secret_ref", None),
                        check_cm=spec.get("check_cm", None),
                        check_url=spec.get("check_url", None),
                    )

                logging.debug(
                    f"{operation} operation detected for thread {thread_name}"
                )

                if operation == "ADDED":
                    # create a new check
                    self._threads[thread_name] = Check(
                        name=name,
                        namespace=namespace,
                        spec=pod_spec,
                        max_attempts=max_attempts,
                        escalations=escalations,
                        pre_status=status,
                        timeout=timeout,
                        metrics_queue=self.metrics_queue,
                        **self.clients,
                        **intervals,
                    )
                elif operation == "DELETED":
                    if thread_name in self._threads:
                        # stop the thread
                        self._threads[thread_name].shutdown()
                        # delete the check object
                        del self._threads[thread_name]
                        logging.info("{thread_name} deleted")
                elif operation == "MODIFIED":
                    # TODO come up with a better way to do this
                    if (
                        self.threads[thread_name].config.spec != pod_spec
                        or self.threads[thread_name].config.notification_interval
                        != intervals["notification_interval"]
                        or self.threads[thread_name].config.check_interval
                        != intervals["check_interval"]
                        or self.threads[thread_name].config.retry_interval
                        != intervals["retry_interval"]
                        or self.threads[thread_name].config.max_attempts != max_attempts
                        or self.threads[thread_name].config.escalations != escalations
                        or self.threads[thread_name].config.timeout != timeout
                    ):
                        logging.info(
                            f"Detected a modification to {thread_name}, restarting the thread"
                        )
                        if thread_name in self.threads:
                            self._threads[thread_name].shutdown()
                            del self._threads[thread_name]
                            self._threads[thread_name] = Check(
                                name=name,
                                namespace=namespace,
                                spec=pod_spec,
                                max_attempts=max_attempts,
                                escalations=escalations,
                                timeout=timeout,
                                metrics_queue=self.metrics_queue,
                                **self.clients,
                                **intervals,
                            )
                    else:
                        logging.debug("Detected a status change")
