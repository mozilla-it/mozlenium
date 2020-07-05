
import logging
import queue
from types import SimpleNamespace
from mozalert.metrics.config import MetricsConfig
from collections import namedtuple

QueueItem = namedtuple("QueueItem", ["key", "name", "namespace", "labels", "value"])

class MetricsQueue:
    def __init__(self):
        self.q = queue.Queue()

    def put(self, key, name, namespace, **kwargs):
        _labels = kwargs.get("labels", {})
        value = kwargs.get("value", None)

        if key not in MetricsConfig.keys():
            return

        labels = {
            "name": name,
            "namespace": namespace,
        }

        for label in _labels.keys():
            if label in MetricsConfig.get(key).get("labels"):
                labels[label] = _labels[label]
            else:
                logging.debug(f"Discarding unused label {label} from {key}")

        self.q.put(QueueItem(key, name, namespace, labels, value))

    def put_many(self, name, namespace, labels, metrics={}):
        """
        metrics are in the form { "key": "val" }
        """
        for key, val in metrics.items():
            self.put(key, name, namespace, labels=labels, value=val)

    def get(self, timeout=3):
        try:
            metric = self.q.get(timeout=timeout)
        except queue.Empty:
            return

        if type(metric) != QueueItem:
            logging.warning("Got a weird queue entry, skipping")
            self.q.task_done()
            return

        key, name, namespace, labels, value = metric

        if key not in MetricsConfig.keys():
            logging.warning(f"{key} not in available metrics, discarding")
            self.q.task_done()
            return

        return SimpleNamespace(
            key=key, name=name, namespace=namespace, labels=labels, value=value
        )

    @property
    def q(self):
        return self._q

    @q.setter
    def q(self, q):
        self._q = q

