from enum import Enum


class Status(Enum):
    """
    mozalert Check Status
    """

    OK = 0
    WARN = 1
    CRITICAL = 2
    UNKNOWN = 3
    PENDING = 4


class State(Enum):
    """
    mozalert Check State
    """

    IDLE = 0
    RUNNING = 1
    UNKNOWN = 2
