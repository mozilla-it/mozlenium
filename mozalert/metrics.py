import os
from time import sleep
import logging

import threading
import queue

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, Counter


class MetricsQueueItem:
    def __init__(self, key, **kwargs):
        self._key = key
        self._name = kwargs.get("name", None)
        self._namespace = kwargs.get("namespace", None)
        self._status = kwargs.get("status", None)
        self._escalated = kwargs.get("escalated", None)
        self._value = kwargs.get("value", None)

    @property
    def key(self):
        return self._key

    @property
    def labels(self):
        return {
            "name": self.name,
            "namespace": self.namespace,
            "status": self.status,
            "escalated": self.escalated,
        }

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace

    @property
    def status(self):
        return self._status

    @property
    def escalated(self):
        return self._escalated

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class MetricsThread(threading.Thread):
    def __init__(self, q, prometheus_gateway=None):
        super().__init__()
        self._shutdown = False
        self.q = q
        self.prometheus_gateway = prometheus_gateway

        if not self.prometheus_gateway:
            self.prometheus_gateway = os.environ.get("PROMETHEUS_GATEWAY", None)

    @property
    def shutdown(self):
        return self._shutdown

    def terminate(self):
        self._shutdown = True

    def run(self):
        """
        Start the metrics queue subscriber which sends metrics to prometheus

        Available metrics are defined here.
        """

        registry = CollectorRegistry()
        # all available metrics
        metrics = {
            "mozalert_check_runtime": Gauge(
                "mozalert_check_runtime",
                "check runtimes",
                ("name", "namespace", "status", "escalated"),
                registry=registry,
            ),
            "mozalert_check_OK_count": Counter(
                "mozalert_check_OK_count",
                "mozalert check OK count",
                ("name", "namespace", "status", "escalated"),
                registry=registry,
            ),
            "mozalert_check_CRITICAL_count": Counter(
                "mozalert_check_CRITICAL_count",
                "mozalert check CRITICAL count",
                ("name", "namespace", "status", "escalated"),
                registry=registry,
            ),
            "mozalert_check_escalations": Gauge(
                "mozalert_check_escalations",
                "mozalert check escalations",
                ("name", "namespace", "status", "escalated"),
                registry=registry,
            ),
        }

        while not self.shutdown:
            try:
                metric = self.q.get(timeout=3)
            except queue.Empty:
                sleep(1)
                continue

            if type(metric) != MetricsQueueItem:
                logging.info("Got a weird queue entry, skipping")
                self.q.task_done()
                continue

            if metric.key not in metrics:
                logging.info(f"{metric.key} not in available metrics, discarding")
                self.q.task_done()
                continue

            prom = metrics[metric.key]

            if metric.value is not None and type(prom) == Gauge:
                prom.labels(**metric.labels).set(metric.value)
            else:
                prom.labels(**metric.labels).inc()

            if self.prometheus_gateway:
                logging.debug("pushing metric to prometheus")
                push_to_gateway(
                    self.prometheus_gateway, job=__name__, registry=registry
                )
            self.q.task_done()
