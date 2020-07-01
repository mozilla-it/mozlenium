from kubernetes import client, config, watch
import os
import logging
import threading
import queue
from time import sleep
import sys
import signal

from mozalert.check import Check
from mozalert.metrics import MetricsThread
from mozalert.service import ServiceEndpoint
from mozalert.event import Event
from mozalert.checkmonitor import CheckMonitor

import re
from datetime import timedelta


class Controller:
    """
    the Controller runs the main thread which tails the event stream for objects in our CRD. It
    manages check threads and ensures they run when/how they're supposed to.
    """

    def __init__(self, **kwargs):
        self.domain = kwargs.get("domain", "crd.k8s.afrank.local")
        self.version = kwargs.get("version", "v1")
        self.plural = kwargs.get("plural", "checks")

        self._check_monitor_interval = kwargs.get("check_monitor_interval", 60)
        self._shutdown = False

        self.metrics_queue = queue.Queue()

        self.setup_client()

        self._checks = {}

        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

    @property
    def checks(self):
        return self._checks

    @property
    def clients(self):
        return self._clients

    @property
    def shutdown(self):
        return self._shutdown

    def terminate(self, signum=-1, frame=None):
        logging.info("Received SIGTERM. Shutting down.")
        self._shutdown = True
        for c in self.checks.keys():
            self._checks[c].terminate()

        self.check_monitor_thread.terminate()
        self.metrics_thread.terminate()
        self.service_thread.terminate()

        for c in self.checks.keys():
            self._checks[c].join()

        sys.exit()

    def setup_client(self):
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

    def kill_check(self, check_name):
        if check_name not in self.checks:
            logging.warning(f"{check_name} not found in checks`")
            return

        self._checks[check_name].terminate()
        del self._checks[check_name]

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

        self.check_monitor_thread = CheckMonitor(
            crd_client=self.clients["crd_client"],
            domain=self.domain,
            version=self.version,
            plural=self.plural,
            interval=self._check_monitor_interval,
        )
        self.check_monitor_thread.start()

        self.metrics_thread = MetricsThread(q=self.metrics_queue)
        self.metrics_thread.start()

        self.service_thread = ServiceEndpoint()
        self.service_thread.start()

        logging.info("Waiting for events...")
        resource_version = ""
        while not self.shutdown:
            stream = watch.Watch().stream(
                self.clients["crd_client"].list_cluster_custom_object,
                self.domain,
                self.version,
                self.plural,
                resource_version=resource_version,
            )
            for crd_event in stream:

                event = Event(**crd_event)

                # restart the controller if ERROR operation is detected.
                # dying is harsh but in theory states should be preserved in the k8s object.
                # I've only seen the ERROR state when applying changes to the CRD definition
                # and in those cases restarting the controller pod is appropriate. TODO validate
                if event.ERROR:
                    logging.error("Received ERROR operation, Dying.")
                    sys.exit()

                if event.BADEVENT:
                    logging.warning(f"Received unexpected {event.type}. Moving on.")
                    continue

                logging.debug(f"{event.type} operation detected for thread {event}")

                check_name = str(event)
                resource_version = event.resource_version

                if event.ADDED:
                    # create a new check and read any
                    # found status back into the check
                    self._checks[check_name] = Check(
                        **self.clients,
                        config=event.config,
                        metrics_queue=self.metrics_queue,
                        pre_status=event.status,
                    )

                if event.DELETED:
                    self.kill_check(check_name)

                if event.MODIFIED:
                    # a MODIFIED event could either be a config change or a status
                    # change, so we need to detect which it is
                    if dict(self.checks[check_name].config) == dict(event.config):
                        logging.debug("Detected a status change")
                        continue

                    logging.info(f"Detected a config change to {event}")

                    self.kill_check(check_name)

                    self._checks[check_name] = Check(
                        **self.clients,
                        config=event.config,
                        metrics_queue=self.metrics_queue,
                    )

        logging.info("Controller shut down")
