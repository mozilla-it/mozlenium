import logging
import threading
from mozalert import checks


class CheckHandler(threading.Thread):
    """
    the CheckHandler thread takes check events from the controller and process them as
    they come in. Each event has an associated operation:

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

    def __init__(self, q, kube, metrics_queue, shutdown=lambda: False):
        super().__init__()
        self.q = q
        self.shutdown = shutdown
        self.kube = kube
        self.metrics_queue = metrics_queue

        self._checks = {}

    @property
    def checks(self):
        return self._checks

    @checks.setter
    def checks(self, checks):
        self._checks = checks

    def terminate(self):
        logging.info("Shutting down checks")
        for c in self.checks.keys():
            self._checks[c].terminate()
        for c in self.checks.keys():
            self._checks[c].thread.join()
        logging.info("Finished shutting down checks")

    def kill_check(self, check_name):
        if check_name not in self.checks:
            logging.warning(f"{check_name} not found in checks`")
            return

        self._checks[check_name].terminate()
        del self._checks[check_name]

    def run(self):
        while not self.shutdown():
            evt = self.q.get()
            if not evt:
                continue

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
                self._checks[check_name] = checks.check.Check(
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

                self._checks[check_name] = checks.check.Check(
                    kube=self.kube,
                    config=evt.config,
                    metrics_queue=self.metrics_queue,
                    pre_status=evt.status,
                )
        self.terminate()
        logging.info("Check Handler Shutdown")
