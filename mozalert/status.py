from enum import Enum
import datetime
import pytz
import logging


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
        if type(next_check) == str and next_check != "None":
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

    def __iter__(self):
        return iter(
            [
                ("status", self.status),
                ("state", self.state),
                ("last_check", self.last_check),
                ("next_check", self.next_check),
                ("attempt", self.attempt),
                ("logs", self.logs),
            ]
        )
