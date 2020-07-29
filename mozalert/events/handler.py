import threading
import logging
import sys

from mozalert import kubeclient
import queue


class EventHandler(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__()
        self.kube = kwargs.get("kube", kubeclient.KubeClient())
        self.shutdown = kwargs.get("shutdown", lambda: False)
        self._stream_watch_timeout = kwargs.get("stream_watch_timeout", 5)

        self.event_queue = kwargs.get("q", queue.Queue())

    def run(self):
        resource_version = ""
        logging.info("Waiting for events...")
        while not self.shutdown():
            stream = self.kube.Watch().stream(
                self.kube.CustomObjectsApi.list_cluster_custom_object,
                self.kube.domain,
                self.kube.version,
                self.kube.plural,
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
        logging.info("Event Handler Shutdown")
