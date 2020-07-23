from enum import Enum
import re
from datetime import timedelta
import logging
import sys

from mozalert.checkconfig import CheckConfig


class EventType(Enum):
    """
    These are the operations our controller supports
    """

    ADDED = 0
    MODIFIED = 1
    DELETED = 2
    ERROR = 3
    BADEVENT = 4


class Event:
    """
    Events come from the k8s event listener as dictionaries
    with the form:

    { 'type': 'ADDED', 'object': <...k8s object...> }

    and in our case the k8s object is a Check object.
    """

    def __init__(self, **kwargs):
        self._type = kwargs.get("type", "BADEVENT")

        self._obj = kwargs.get("object", {})
        self._check_spec = self._obj.get("spec", {})
        self._status = self._obj.get("status", {})
        self._metadata = self._obj.get("metadata", {})

        self._resource_version = self._metadata.get("resourceVersion")
        self._image = self._check_spec.get("image", None)

        self.config = CheckConfig(
            name=self._metadata.get("name"),
            namespace=self._metadata.get("namespace"),
            check_interval=self.parse_time(
                self._check_spec.get("check_interval")
            ).seconds,
            retry_interval=self.parse_time(
                self._check_spec.get("retry_interval")
            ).seconds,
            notification_interval=self.parse_time(
                self._check_spec.get("notification_interval")
            ).seconds,
            escalations=self._check_spec.get("escalations", []),
            max_attempts=self._check_spec.get("max_attempts", 3),
            timeout=self.parse_time(self._check_spec.get("timeout", "5m")).seconds,
            pod_spec=self._check_spec.get("template", {}).get("spec", {}),
        )

        if not self.config.pod_spec:
            self.config.build_pod_spec(**self._check_spec)

    @property
    def obj(self):
        return self._obj

    @property
    def type(self):
        if self._type not in [x.name for x in EventType]:
            return EventType.BADEVENT
        return getattr(EventType, self._type)

    @property
    def resource_version(self):
        """
        the resourceVersion is what k8s uses to keep track of
        changes in objects; we keep this number handy so when we
        pull new events from the event listener we can start at the
        most recent resource version we know about.
        """
        return self._resource_version

    @property
    def status(self):
        return self._status

    @property
    def ADDED(self):
        return self.type == EventType.ADDED

    @property
    def MODIFIED(self):
        return self.type == EventType.MODIFIED

    @property
    def DELETED(self):
        return self.type == EventType.DELETED

    @property
    def ERROR(self):
        return self.type == EventType.ERROR

    @property
    def BADEVENT(self):
        return self.type == EventType.BADEVENT

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    def __repr__(self):
        return f"{self.config.namespace}/{self.config.name}"

    def __str__(self):
        return f"{self.config.namespace}/{self.config.name}"

    @property
    def image(self):
        return self._image

    @staticmethod
    def parse_time(time_str):
        """
        parse_time takes either a number (in minutes) or a formatted time string [XXh][XXm][XXs]
        """
        try:
            minutes = float(time_str)
            return timedelta(minutes=minutes)
        except:
            # didn't pass a number, move on to parse the string
            pass
        regex = re.compile(
            r"((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?"
        )
        try:
            parts = regex.match(time_str)
        except Exception as e:
            logging.error(e)
            logging.error(sys.exc_info()[0])
            return timedelta(minutes=0)
        if not parts:
            return timedelta(minutes=0)
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in iter(parts.items()):
            if param:
                time_params[name] = int(param)
        return timedelta(**time_params)
