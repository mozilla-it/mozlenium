from enum import Enum

class Status(Enum):
    OK = 0
    WARN = 1
    CRITICAL = 2
    UNKNOWN = 3
    PENDING = 4

class State(Enum):
    IDLE = 0
    RUNNING = 1
    UNKNOWN = 2
