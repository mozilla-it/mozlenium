import threading
import logging
from time import sleep
from mozalert import status, events

# from mozalert.status import Status
# from mozalert.event import Event
from mozalert.utils.dt import now
import pytz
import datetime


class CheckMonitor(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__()
        self.kube = kwargs.get("kube")
        self.domain = kwargs.get("domain")
        self.version = kwargs.get("version")
        self.plural = kwargs.get("plural")

        self.interval = kwargs.get("interval", 60)

        self.shutdown = kwargs.get("shutdown", lambda: False)

        # max failures before considering the check run a failure
        self.failed_threshold = kwargs.get("failed_threshold", 0)

        self.sequential_failed_run_threshold = kwargs.get(
            "sequential_failed_run_threshold", 2
        )

        self.sequential_failed_runs = 0

        self.setName("check-monitor")

    def terminate(self):
        return self.join()

    def run(self):
        t = 1
        while not self.shutdown():
            tsleep = 0
            while tsleep < self.interval:
                sleep(t)
                tsleep += t
                if self.shutdown():
                    logging.info("Received SIGTERM, shutting down.")
                    return
            self.check_monitor()
        logging.info("Received SIGTERM, shutting down.")

    def check_monitor(self):
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

        success = 0
        failed = 0

        logging.info("Running Check Monitor")

        checks = {}
        try:
            check_list = self.kube.CustomObjectsApi.list_cluster_custom_object(
                self.domain, self.version, self.plural, watch=False
            )
        except Exception as e:
            logging.error(e)
            check_list = {"items": []}

        for obj in check_list.get("items"):
            evt = events.event.Event(type="ADD", object=obj)
            st = status.Status(**evt.status)
            name = str(evt)

            # do some sanity checks
            if (
                not st.next_check
                or pytz.utc.localize(st.next_check) + datetime.timedelta(seconds=30)
                < now()
            ) and not st.RUNNING:
                failed += 1
                logging.warning(
                    f"Sanity check failed: {name} next_check is in the past but status is not RUNNING"
                )
            else:
                success += 1

        if failed > self.failed_threshold:
            self.sequential_failed_runs += 1
            logging.warning(
                f"Sequential Failed Sanity Checks: {self.sequential_failed_runs}"
            )
        else:
            self.sequential_failed_runs = 0

        logging.debug(
            f"sanity check finished with {success} success and {failed} failures"
        )

        if self.sequential_failed_runs > self.sequential_failed_run_threshold:
            logging.error(
                f"Circuit breaker triggered: Sanity Check Sequential Failures {self.sequential_failed_runs} > {self.sequential_failed_run_threshold}"
            )

        logging.info("Check Monitor finished")
