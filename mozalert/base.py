import os
import sys
import logging
import threading

from types import SimpleNamespace
import datetime
import pytz

from mozalert.state import State, Status
from mozalert.sendgrid import SendGridTools


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
        self._job_poll_interval = float(kwargs.get("job_poll_interval", 3))
        default_escalation_template = """
        <p>
        <b>Name:</b> {namespace}/{name}<br>
        <b>Status:</b> {status}<br>                            
        <b>Attempt:</b> {attempt}/{max_attempts}<br>
        <b>Last Check:</b> {last_check}<br>
        <b>More Details:</b><br> <pre>{logs}</pre><br>
        </p>
        """
        self._config = SimpleNamespace(
            name = kwargs.get("name"),
            namespace = kwargs.get("namespace"),
            check_interval = float(kwargs.get("check_interval")),
            retry_interval = float(kwargs.get("retry_interval", 0)),
            notification_interval = float(kwargs.get("notification_interval", 0)),
            spec = kwargs.get("spec", {}),
            escalation = kwargs.get("escalation", ""),
            max_attempts = int(kwargs.get("max_attempts", "3")),
            escalation_template = kwargs.get("escalation_template", default_escalation_template),
        )

        self._update = kwargs.get("update", False)

        if not self._config.retry_interval:
            self._config.retry_interval = self._config.check_interval
        if not self._config.notification_interval:
            self._config.notification_interval = self._config.check_interval

        # initialize the check for the first time
        if not self._update:
            self._shutdown = False
            self._attempt = 0
            self._runtime = 0
            self._last_check = None
            self._next_check = None
            self._logs = ""

            self._status = Status.PENDING
            self._state = State.IDLE

            self._thread = None

            self._next_interval = self._config.check_interval

            self.start_thread()
            self.set_crd_status()

    @property
    def config(self):
        return self._config

    @property
    def thread(self):
        return self._thread

    def __repr__(self):
        return f"{self._config.namespace}/{self._config.name}"

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

    def escalate(self):
        logging.info(f"Escalating {self._config.namespace}/{self._config.name}")
        sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
        message = self._config.escalation_template.format(
            name=self._config.name,
            namespace=self._config.namespace,
            status=self._status.name,
            attempt=self._attempt,
            max_attempts=self._config.max_attempts,
            last_check=str(self._last_check),
            logs=self._logs,
        )
        SendGridTools.send_message(
            api_key=sendgrid_key,
            to_emails=[self._config.escalation],
            message=message,
            subject=f"Mozalert {self._status.name}: {self._config.namespace}/{self._config.name}",
        )
        logging.info(f"Message sent to {self._escalation}")

    def shutdown(self):
        """
        stop the thread and cleanup any leftover jobs
        """
        self._shutdown = True
        logging.debug(
            f"Stopping check thread for {self._config.namespace}/{self._config.name}"
        )
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
            f"Running the check thread instance for {self._config.namespace}/{self._config.name}"
        )
        self._attempt += 1
        # run the job; this blocks until completion
        self.run_job()
        logging.info(f"Check finished for {self._config.namespace}/{self._config.name}")
        logging.debug(
            f"Cleaning up finished job for {self._config.namespace}/{self._config.name}"
        )
        self.delete_job()
        if self._status == Status.OK:
            # check passed, things are great!
            self._attempt = 0
            self._next_inteval = self._config.check_interval
        elif self._attempt >= self._config.max_attempts:
            # state is not OK and we've run out of attempts. do the escalation
            self.escalate()
            self._next_interval = self._config.notification_interval
            # ^ TODO keep retrying after escalation? giveup? reset?
        else:
            # not state OK and not enough failures to escalate
            self._next_interval = self._config.retry_interval

        # set the next_check for the CRD status
        self._next_check = pytz.utc.localize(
            datetime.datetime.utcnow()
        ) + datetime.timedelta(seconds=self._next_interval)
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
            f"Starting check thread for {self._config.namespace}/{self._config.name} at interval {self._next_interval} seconds"
        )

        self._thread = threading.Timer(self._next_interval, self.check)
        self._thread.setName(f"{self._config.namespace}/{self._config.name}")
        self._thread.start()

        self._next_check = pytz.utc.localize(
            datetime.datetime.utcnow()
        ) + datetime.timedelta(seconds=self._next_interval)
