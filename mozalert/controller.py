import logging
import threading
import queue

from mozalert import kubeclient, check, metrics, event, checkmonitor

class Controller(threading.Thread):
    """
    the Controller runs the main thread which tails the event stream for objects in our CRD. It
    manages check threads and ensures they run when/how they're supposed to.
    """

    def __init__(self, **kwargs):
        super().__init__()

        self.domain = kwargs.get("domain", "crd.k8s.afrank.local")
        self.version = kwargs.get("version", "v1")
        self.plural = kwargs.get("plural", "checks")

        self.shutdown = kwargs.get("shutdown", lambda: False)

        self.metrics_thread_shutdown = False
        self.check_monitor_thread_shutdown = False
        self._check_monitor_interval = kwargs.get("check_monitor_interval", 60)

        self.watch = None

        self.metrics_queue = metrics.queue.MetricsQueue()

        self.kube = kubeclient.KubeClient()

        self._checks = {}

        self.setName("controller-thread")

    @property
    def checks(self):
        return self._checks

    @property
    def clients(self):
        return self._clients

    def terminate(self):
        logging.info("Received SIGTERM request. Shutting down controller.")

        for c in self.checks.keys():
            self._checks[c].terminate()

        self.check_monitor_thread_shutdown = True
        self.metrics_thread_shutdown = True

        for c in self.checks.keys():
            self._checks[c].thread.join()
        logging.info("finished joining checks")

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

        self.check_monitor_thread = checkmonitor.CheckMonitor(
            kube=self.kube,
            domain=self.domain,
            version=self.version,
            plural=self.plural,
            interval=self._check_monitor_interval,
            shutdown=lambda: self.check_monitor_thread_shutdown,
        )
        self.check_monitor_thread.start()

        # start the metrics consumer
        self.metrics_thread = metrics.thread.MetricsThread(
            q=self.metrics_queue, shutdown=lambda: self.metrics_thread_shutdown
        )
        self.metrics_thread.start()

        logging.info("Waiting for events...")
        resource_version = ""
        while not self.shutdown():
            self.watch = self.kube.Watch()
            stream = self.watch.stream(
                self.kube.CustomObjectsApi.list_cluster_custom_object,
                self.domain,
                self.version,
                self.plural,
                resource_version=resource_version,
                timeout_seconds=5,  # TODO parameterize this timeout
            )
            for crd_event in stream:
                evt = event.Event(**crd_event)

                # restart the controller if ERROR operation is detected.
                if evt.ERROR:
                    logging.error("Received ERROR operation, Dying.")
                    self.terminate()
                    return

                if evt.BADEVENT:
                    logging.warning(f"Received unexpected {evt.type}. Moving on.")
                    continue

                logging.debug(f"{evt.type} operation detected for thread {evt}")

                check_name = str(evt)
                resource_version = evt.resource_version

                if evt.ADDED:
                    # create a new check and read any
                    # found status back into the check
                    self._checks[check_name] = check.Check(
                        kube=self.kube,
                        config=evt.config,
                        metrics_queue=self.metrics_queue,
                        pre_status=evt.status,
                    )

                if evt.DELETED:
                    self.kill_check(check_name)

                if evt.MODIFIED:
                    # a MODIFIED event could either be a config change or a status
                    # change, so we need to detect which it is
                    if dict(self.checks[check_name].config) == dict(evt.config):
                        logging.debug("Detected a status change")
                        continue

                    logging.info(f"Detected a config change to {evt}")

                    self.kill_check(check_name)

                    self._checks[check_name] = check.Check(
                        kube=self.kube,
                        config=evt.config,
                        metrics_queue=self.metrics_queue,
                        pre_status=evt.status,
                    )

        logging.info("Controller shut down")
