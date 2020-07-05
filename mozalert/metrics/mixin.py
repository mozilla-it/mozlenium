
import logging
import re

class MetricsMixin:
    """
    MetricsMixin adds the methods needed to send metrics
    """

    def __init__(self, **kwargs):
        self.metrics_queue = kwargs.get("metrics_queue", None)

    @property
    def metric_labels(self):
        """
        A dictionary of labels used by metrics
        """
        return {
            "escalated": self.escalated,
            "status": self.status.status.name,
        }

    @property
    def metric_values(self):
        v = {
            "mozalert_check_runtime": self._runtime.seconds,
            "mozalert_check_failures": int(self.status.CRITICAL),
            "mozalert_check_escalations": int(self.escalated),
        }
        for t in self.status.telemetry.keys():
            v[f"mozalert_check_{t}"] = float(self.status.telemetry[t])

        return v

    @staticmethod
    def extract_telemetry_from_logs(logs):
        """
        we support some basic telemetry in log responses from checks. 
        this allows one to pass telemetry back to the controller
        without needing to implement additional clients.
        """
        _logs = ""
        _telemetry = {}
        for line in logs.split("\n"):
            pattern = re.compile(r"TELEMETRY:\s*(?P<key>\w+)\s*(?P<val>\d+)[^0-9]?")
            match = pattern.match(line)
            if not match:
                _logs += line + "\n"
                continue
            m = match.groupdict()
            key = m.get("key")
            val = m.get("val")
            _telemetry[key] = val

        return _logs, _telemetry

