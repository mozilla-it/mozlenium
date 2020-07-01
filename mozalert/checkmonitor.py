import threading
import logging
from time import sleep
from mozalert.status import Status
from mozalert.event import Event
import pytz
import datetime


class CheckMonitor(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__()
        self.crd_client = kwargs.get("crd_client")
        self.domain = kwargs.get("domain")
        self.version = kwargs.get("version")
        self.plural = kwargs.get("plural")

        self.interval = kwargs.get("interval", 60)

        self._shutdown = False

        self.setName("check-monitor")

    @property
    def shutdown(self):
        return self._shutdown

    def terminate(self):
        self._shutdown = True

    def run(self):
        while not self.shutdown:
            sleep(self.interval)
            self.check_monitor()

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

        logging.info("Running Cluster Monitor")

        checks = {}
        try:
            check_list = self.crd_client.list_cluster_custom_object(
                self.domain, self.version, self.plural, watch=False
            )
        except Exception as e:
            logging.error(e)
            check_list = {"items": []}

        for obj in check_list.get("items"):
            event = Event(type="ADD", object=obj)
            status = Status(**event.status)
            now = pytz.utc.localize(datetime.datetime.utcnow())
            name = str(event)

            # do some sanity checks
            if (
                not status.next_check
                or pytz.utc.localize(status.next_check) + datetime.timedelta(seconds=30)
                < now
            ) and not status.RUNNING:
                failed += 1
                logging.warning(
                    "Sanity check failed: {name} next_check is in the past but status is not RUNNING"
                )
            else:
                success += 1

        logging.debug(
            f"sanity check finished with {success} success and {failed} failures"
        )

        logging.info("Cluster Monitor finished")
