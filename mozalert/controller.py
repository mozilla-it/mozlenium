from kubernetes import client, config, watch
import os
import logging

from mozalert.check import Check

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

    @staticmethod
    def build_spec(name, image, secretRef, check_cm):
        return {
            "restart_policy": "Never",
            "containers": [
                {
                    "name": name,
                    "image": image,
                    "envFrom": [ { "secretRef": { "name": secretRef } } ],
                    "volumeMounts": [ { "name": "checks", "mountPath": "/checks", "readOnly": True } ]
                }
            ],
            "volumes": [ { "name": "checks", "configMap": { "name": check_cm } } ]
        }

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
        regex = re.compile(r'((?P<hours>\d+?)hr)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
        parts = regex.match(time_str)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in iter(parts.items()):
            if param:
                time_params[name] = int(param)
        return timedelta(**time_params)

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

        logging.info("Waiting for events...")
        resource_version = ""
        while True:
            stream = watch.Watch().stream(
                self._clients["crd_client"].list_cluster_custom_object,
                self._domain,
                self._version,
                self._plural,
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
                intervals = {
                    "check_interval": self.parse_time(spec.get("check_interval")).seconds,
                    "retry_interval": self.parse_time(spec.get("retry_interval", "")).seconds,
                    "notification_interval": self.parse_time(spec.get("notification_interval", "")).seconds,
                }
                max_attempts = spec.get("max_attempts",3)

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
                pod_template = spec.get("template", {})
                pod_spec = pod_template.get("spec", {})
                if not pod_spec:
                    pod_spec = self.build_spec(
                        name = name,
                        image = spec.get("image",None),
                        secretRef = spec.get("secretRef",None),
                        check_cm = spec.get("check_cm",None)
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
                        **self._clients,
                        **intervals,
                    )
                elif operation == "DELETED":
                    if thread_name in self._threads:
                        # stop the thread
                        self._threads[thread_name].shutdown()
                        # delete the check object
                        del self._threads[thread_name]
                elif operation == "MODIFIED":
                    # TODO come up with a better way to do this
                    if (
                        self._threads[thread_name].spec != pod_spec
                        or self._threads[thread_name].notification_interval != intervals["notification_interval"]
                        or self._threads[thread_name].check_interval != intervals["check_interval"]
                        or self._threads[thread_name].retry_interval != intervals["retry_interval"]
                        or self._threads[thread_name].max_attempts != max_attempts
                    ):
                        logging.info(f"Detected a modification to {thread_name}, restarting the thread")
                        if thread_name in self._threads:
                            self._threads[thread_name].shutdown()
                            del self._threads[thread_name]
                            self._threads[thread_name] = Check(
                                name=name,
                                namespace=namespace,
                                spec=pod_spec,
                                max_attempts=max_attempts,
                                **self._clients,
                                **intervals,
                            )
                    else:
                        logging.debug("Detected a status change")
