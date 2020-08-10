from enum import Enum
import datetime
import pytz
import logging

from mozalert.utils.dt import now


class EnumStatus(Enum):
    """
    mozalert Check Status
    """

    OK = 0
    WARN = 1
    CRITICAL = 2
    UNKNOWN = 3
    PENDING = 4


class EnumState(Enum):
    """
    mozalert Check State
    """

    IDLE = 0
    RUNNING = 1
    UNKNOWN = 2


class Status:
    """
    the status object is our python representation of the 
    status subresource in our check crd object. 
    """

    def __init__(self, **kwargs):
        self.status = kwargs.get("status", "PENDING")
        self.state = kwargs.get("state", "IDLE")
        self.last_check = kwargs.get("last_check", None)
        self.next_check = kwargs.get("next_check", None)
        self.attempt = kwargs.get("attempt", 0)
        self.logs = kwargs.get("logs", "")
        self.message = kwargs.get("message","")
        self.telemetry = kwargs.get("telemetry", {})

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if type(status) == str:
            status = getattr(EnumStatus, status)
        logging.debug(f"setting status to {status.name}")
        self._status = status

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        if type(state) == str:
            state = getattr(EnumState, state)
        logging.debug(f"setting state to {state.name}")
        self._state = state

    @property
    def telemetry(self):
        return self._telemetry

    @telemetry.setter
    def telemetry(self, telemetry):
        self._telemetry = telemetry

    @property
    def last_check(self):
        return self._last_check

    @last_check.setter
    def last_check(self, last_check):
        if type(last_check) == str and last_check != "None":
            try:
                last_check = datetime.datetime.strptime(
                    last_check, "%Y-%m-%d %H:%M:%S%z"
                )
                self._last_check = last - check
                return
            except:
                pass
            last_check = datetime.datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
        self._last_check = last_check

    @property
    def next_check(self):
        return self._next_check

    @next_check.setter
    def next_check(self, next_check):
        logging.debug(f"Attempting to set next_check {next_check}")
        if next_check and type(next_check) == str and next_check != "None":
            try:
                next_check = datetime.datetime.strptime(
                    next_check, "%Y-%m-%d %H:%M:%S%z"
                )
                self._next_check = next_check
                return
            except:
                pass
            next_check = datetime.datetime.strptime(next_check, "%Y-%m-%d %H:%M:%S")
        self._next_check = next_check

    @property
    def attempt(self):
        return self._attempt

    @attempt.setter
    def attempt(self, attempt):
        self._attempt = int(attempt)

    @property
    def logs(self):
        return self._logs

    @logs.setter
    def logs(self, logs):
        self._logs = logs

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, message):
        self._message = message

    def __iter__(self):
        return iter(
            [
                ("status", self.status),
                ("state", self.state),
                ("last_check", self.last_check),
                ("next_check", self.next_check),
                ("attempt", self.attempt),
                ("logs", self.logs),
                ("telemetry", self.telemetry),
                ("message", self.message),
            ]
        )

    @property
    def OK(self):
        return self.status == EnumStatus.OK

    @property
    def WARN(self):
        return self.status == EnumStatus.WARN

    @property
    def CRITICAL(self):
        return self.status == EnumStatus.CRITICAL

    @property
    def PENDING(self):
        return self.status == EnumStatus.PENDING

    @property
    def IDLE(self):
        return self.state == EnumState.IDLE

    @property
    def RUNNING(self):
        return self.state == EnumState.RUNNING

    @property
    def crd_status(self):
        # TODO combine with __iter__
        return {
            "status": {
                "status": str(self.status.name),
                "state": str(self.state.name),
                "attempt": str(self.attempt),
                "last_check": str(self.last_check).split(".")[0],
                "next_check": str(self.next_check).split(".")[0],
                "logs": self.logs,
                "telemetry": self.telemetry,
                "message": self.message,
            }
        }

    @property
    def next_interval(self):
        if not self.next_check:
            return 0
        next_check = pytz.utc.localize(self.next_check)
        if now() > next_check:
            return 1
        else:
            return (next_check - now()).seconds

    def parse_pre_status(self, **kwargs):
        self.status = kwargs.get("status", self.status)
        self.state = kwargs.get("state", self.state)
        self.last_check = kwargs.get("last_check", self.last_check)
        self.next_check = kwargs.get("next_check", self.next_check)
        self.attempt = kwargs.get("attempt", self.attempt)
        self.logs = kwargs.get("logs", self.logs)
        self.telemetry = kwargs.get("telemetry", self.telemetry)
        self.message = kwargs.get("message", self.message)
        if self.RUNNING and self.attempt:
            # pre_status was running with an attempt >0 so decrement the attempt
            # since we will retry anyhow
            self.attempt -= 1
