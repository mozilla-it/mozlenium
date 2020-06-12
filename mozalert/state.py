from enum import Enum

class State(Enum):
    OK = 0
    WARN = 1
    CRITICAL = 2
    UNKNOWN = 3
    RETRY = 4
    RUNNING = 5
    NEW = 6
