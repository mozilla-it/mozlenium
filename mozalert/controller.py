import logging
import threading
import queue
import sys
from types import SimpleNamespace
from time import sleep

from mozalert import kubeclient, checks, metrics, events


class Controller(threading.Thread):
    """
    the Controller runs the main thread which tails the event stream for objects in the CRD. It
    manages threads, including an event handler, and makes sure things run how they're supposed to.
    """

    def __init__(self, **kwargs):
        super().__init__()

        self.domain = kwargs.get("domain", "crd.k8s.afrank.local")
        self.version = kwargs.get("version", "v1")
        self.plural = kwargs.get("plural", "checks")

        self.shutdown = kwargs.get("shutdown", lambda: False)

        self._check_monitor_interval = kwargs.get("check_monitor_interval", 60)
        self._stream_watch_timeout = kwargs.get("stream_watch_timeout", 5)

        self.metrics_queue = metrics.queue.MetricsQueue()
        self.event_queue = events.queue.EventQueue()

        self.kube = kubeclient.KubeClient()

        self.threads = {}

        self.setName("controller-thread")

    @property
    def clients(self):
        return self._clients

    @property
    def checks(self):
        return self.threads["check-handler"].thread.checks

    def terminate(self):
        logging.info("Received SIGTERM request. Shutting down controller.")
        for t in self.threads.keys():
            self.threads[t].shutdown = True

    def new_thread(self, name, obj, **kwargs):
        self.threads[name] = SimpleNamespace()
        self.threads[name].shutdown = False
        self.threads[name].obj = obj
        self.threads[name].kwargs = kwargs
        self.threads[name].thread = obj(
            **kwargs, shutdown=lambda: self.threads[name].shutdown
        )
        self.threads[name].thread.setName(name)
        self.threads[name].thread.start()

    def restart_thread(self, name):
        if name not in self.threads:
            logging.error(f"{name} is not a valid thread")
            return
        if self.threads[name].thread.is_alive():
            logging.info(f"Trying to restart {name} but it's still running, attempting to shut down")
            self.threads[name].shutdown = True
            self.threads[name].thread.join()

        self.new_thread(
            name,
            self.threads[name].obj,
            **self.threads[name].kwargs,
        )

    def run(self):
        """
        the controller thread runs various threads:
           * healthcheck
           * metrics
           * event handler
           * check handler
        """

        # start the check_monitor thread
        self.new_thread(
            "healthcheck-thread",
            checks.monitor.CheckMonitor,
            kube=self.kube,
            domain=self.domain,
            version=self.version,
            plural=self.plural,
            interval=self._check_monitor_interval,
        )

        # start the metrics consumer
        self.new_thread(
            "metrics-handler", metrics.thread.MetricsThread, q=self.metrics_queue
        )

        # start the event handler
        self.new_thread(
            "event-handler",
            events.thread.EventThread,
            q=self.event_queue,
            kube=self.kube,
            domain=self.domain,
            version=self.version,
            plural=self.plural,
        )

        # start the check handler
        self.new_thread(
            "check-handler",
            checks.handler.CheckHandler,
            q=self.event_queue,
            kube=self.kube,
            metrics_queue=self.metrics_queue,
        )

        while not self.shutdown():
            for t in self.threads.keys():
                if not self.shutdown() and not self.threads[t].thread.is_alive():
                    logging.error(f"Thread {t} was not running. Restarting.")
                    self.restart_thread(t)
            sleep(2)

        # main loop is broken so shut down
        for t in self.threads.keys():
            self.threads[t].thread.join()
        logging.info("Controller shut down")
