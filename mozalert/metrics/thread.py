import os
import logging

import threading
import queue

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, Counter

from mozalert.metrics.config import MetricsConfig

SupportedMetricTypes = ["Counter", "Gauge"]


class MetricsThread(threading.Thread):
    def __init__(self, q, shutdown=lambda: False, prometheus_gateway=None):
        super().__init__()
        # metrics_queue object
        self.q = q
        self.prometheus_gateway = prometheus_gateway
        self.shutdown = shutdown

        if not self.prometheus_gateway:
            self.prometheus_gateway = os.environ.get("PROMETHEUS_GATEWAY", None)

    def terminate(self):
        return self.join()

    def run(self):
        """
        Start the metrics queue subscriber which sends metrics to prometheus
        """

        registry = CollectorRegistry()
        metrics = {}
        # read the metrics config into a dictionary and set up the registry
        # for recording metrics from the queue. When metrics come in from
        # the queue they are added to these metrics and submitted to
        # prometheus each time a new data point is added.
        for m in MetricsConfig.keys():
            c = MetricsConfig[m]
            # add name/namespace to any user-defined labels
            l = tuple(set(c.get("labels", []) + ["name", "namespace"]))
            t = c.get("type", "")
            if t not in SupportedMetricTypes:
                logging.error(f"Discarding unsupported metric type {t}")
            func = eval(t)
            metrics[m] = func(m, m, l, registry=registry)

        while not self.shutdown():

            metric = self.q.get()
            if not metric:
                continue

            try:
                prom = metrics[metric.key]

                logging.debug(
                    f"Recording metric for {metric.key} value {metric.value} labels {metric.labels}"
                )

                if metric.value is not None and type(prom) == Gauge:
                    prom.labels(**metric.labels).set(metric.value)
                else:
                    prom.labels(**metric.labels).inc()

                if self.prometheus_gateway:
                    logging.debug("pushing metric to prometheus")
                    push_to_gateway(
                        self.prometheus_gateway,
                        job="mozalert.metrics",
                        registry=registry,
                    )
            except Exception as e:
                logging.info(e)
