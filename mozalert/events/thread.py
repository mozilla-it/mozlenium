import threading
import logging
import sys


class EventThread(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__()
        self.kube = kwargs.get("kube")
        self.domain = kwargs.get("domain")
        self.version = kwargs.get("version")
        self.plural = kwargs.get("plural")
        self.shutdown = kwargs.get("shutdown")
        self._stream_watch_timeout = kwargs.get("stream_watch_timeout", 5)
        self.event_queue = kwargs.get("q")

    def run(self):
        resource_version = ""
        logging.info("Waiting for events...")
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
        logging.info("Event Handler Shutdown")
