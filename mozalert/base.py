import sys
import logging
import threading

from types import SimpleNamespace
import datetime
import pytz

from mozalert.state import State, Status


class BaseCheck:
    """
    BaseCheck implements the thread/interval logic of a check without any
    actual execution.

    To use this class as your base class, you should implement the
    job-related methods:
        * delete_job
        * get_job_logs (string)
        * get_job_status (SimpleNamespace)
        * set_crd_status
        * run_job
    """

    def __init__(self, **kwargs):
        """
        initialize/reinitialize a check
        """
        self._name = kwargs.get("name")
        self._namespace = kwargs.get("namespace")
        self._check_interval = float(kwargs.get("check_interval"))
        self._retry_interval = float(kwargs.get("retry_interval", 0))
        self._notification_interval = float(kwargs.get("notification_interval", 0))
        self._job_poll_interval = float(kwargs.get("job_poll_interval", 3))
        self._spec = kwargs.get("spec",{})

        self._max_attempts = int(kwargs.get("max_attempts", "3"))

        self._update = kwargs.get("update", False)

        if not self._retry_interval:
            self._retry_interval = self._check_interval
        if not self._notification_interval:
            self._notification_interval = self._check_interval

        # initialize the check for the first time
        if not self._update:
            self._shutdown = False
            self._attempt = 0
            self._runtime = 0
            self._last_check = None
            self._next_check = None

            self._status = Status.PENDING
            self._state = State.IDLE

            self._thread = None

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

    @property
    def thread(self):
        return self._thread

    @property
    def check_interval(self):
        return self._check_interval

    @property
    def retry_interval(self):
        return self._retry_interval

    @property
    def notification_interval(self):
        return self._notification_interval

    @property
    def max_attempts(self):
        return self._max_attempts

    def __repr__(self):
        return f"{self._namespace}/{self._name}"

    def run_job(self):
        logging.info("Executing mock run_job")

    def set_crd_status(self):
        logging.info("Executing mock set_crd_status")

    def get_job_status(self):
        logging.info("Executing mock set_status")
        return SimpleNamespace(
            active=False, succeeded=False, failed=False, start_time=None
        )

    def get_job_logs(self):
        logging.info("Executing mock get_job_logs")
        return ""

    def delete_job(self):
        logging.info("Executing mock delete_job")

    def shutdown(self):
        """
        stop the thread and cleanup any leftover jobs
        """
        self._shutdown = True
        logging.debug(f"Stopping check thread for {self._namespace}/{self._name}")
        if self._thread:
            try:
                self._thread.cancel()
                self._thread.join()
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
        # run the job; this blocks until completion
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
        self._next_check = pytz.utc.localize(datetime.datetime.utcnow()) + datetime.timedelta(seconds=self._next_interval)
        if not self._shutdown:
            # officially schedule the next run
            self.start_thread()
            # update the CRD status subresource
            self.set_crd_status()

    def start_thread(self):
        """
        starts the thread and updates the next_check time in the object.

        For this to work you must have a self.check and a self._next_interval >=0 seconds
        """
        logging.info(
            f"Starting check thread for {self._namespace}/{self._name} at interval {self._next_interval} seconds"
        )

        self._thread = threading.Timer(self._next_interval, self.check)
        self._thread.setName(f"{self._namespace}/{self._name}")
        self._thread.start()

        self._next_check = pytz.utc.localize(datetime.datetime.utcnow()) + datetime.timedelta(seconds=self._next_interval)
