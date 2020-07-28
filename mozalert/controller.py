import logging
import threading
import queue
import sys

from mozalert import kubeclient, checkevent, checks, metrics, events


class Controller(threading.Thread):
    """
    the Controller runs the main thread which tails the event stream for objects in our CRD. It
    manages threads, including an event handler, and makes sure things run how they're supposed to.
    """

    def __init__(self, **kwargs):
        super().__init__()

        self.domain = kwargs.get("domain", "crd.k8s.afrank.local")
        self.version = kwargs.get("version", "v1")
        self.plural = kwargs.get("plural", "checks")

        self.shutdown = kwargs.get("shutdown", lambda: False)

        self.metrics_thread_shutdown = False
        self.check_monitor_thread_shutdown = False
        self.event_handler_thread_shutdown = False

        self._check_monitor_interval = kwargs.get("check_monitor_interval", 60)
        self._stream_watch_timeout = kwargs.get("stream_watch_timeout", 5)

        self.metrics_queue = metrics.queue.MetricsQueue()
        self.event_queue = events.queue.EventQueue()

        self.kube = kubeclient.KubeClient()

        self.setName("controller-thread")

    @property
    def clients(self):
        return self._clients

    @property
    def handler(self):
        return self.event_handler_thread

    def terminate(self):
        logging.info("Received SIGTERM request. Shutting down controller.")
        self.event_handler_thread_shutdown = True
        self.check_monitor_thread_shutdown = True
        self.metrics_thread_shutdown = True

    def run(self):
        # start the check_monitor thread
        self.check_monitor_thread = checks.monitor.CheckMonitor(
            kube=self.kube,
            domain=self.domain,
            version=self.version,
            plural=self.plural,
            interval=self._check_monitor_interval,
            shutdown=lambda: self.check_monitor_thread_shutdown,
        )
        self.check_monitor_thread.start()

        # start the metrics consumer
        self.metrics_thread = metrics.thread.MetricsThread(
            q=self.metrics_queue, shutdown=lambda: self.metrics_thread_shutdown
        )
        self.metrics_thread.start()

        # start the event handler
        self.event_handler_thread = checkevent.EventHandler(
            q=self.event_queue,
            kube=self.kube,
            metrics_queue=self.metrics_queue,
            shutdown=lambda: self.event_handler_thread_shutdown,
        )
        self.event_handler_thread.start()

        logging.info("Waiting for events...")
        resource_version = ""
        while not self.shutdown():
            watch = self.kube.Watch()
            stream = watch.stream(
                self.kube.CustomObjectsApi.list_cluster_custom_object,
                self.domain,
                self.version,
                self.plural,
                resource_version=resource_version,
                timeout_seconds=self._stream_watch_timeout,
            )
            for crd_event in stream:
                # add events to the event queue
                try:
                    resource_version = (
                        crd_event.get("object", {})
                        .get("metadata", {})
                        .get("resourceVersion", "")
                    )
                    self.event_queue.put(**crd_event)
                except Exception as e:
                    logging.error(e)
                    logging.error(sys.exc_info()[0])

        # main loop is broken so shut down
        self.check_monitor_thread.join()
        self.metrics_thread.join()
        self.event_handler_thread.join()
        logging.info("Controller shut down")
