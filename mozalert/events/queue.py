import logging
import queue
from types import SimpleNamespace
from mozalert.events.event import Event

# from collections import namedtuple
import sys

# QueueItem = namedtuple("QueueItem", ["key", "name", "namespace", "labels", "value"])


class EventQueue:
    def __init__(self):
        self.q = queue.Queue()

    def put(self, **kwargs):
        try:
            evt = Event(**kwargs)
            self.q.put(evt)
        except Exception as e:
            logging.error("Queue Error")
            logging.error(e)
            logging.error(sys.exc_info()[0])

    def get(self, timeout=3):
        try:
            evt = self.q.get(timeout=timeout)
        except queue.Empty:
            return

        self.q.task_done()
        return evt

    @property
    def q(self):
        return self._q

    @q.setter
    def q(self, q):
        self._q = q
