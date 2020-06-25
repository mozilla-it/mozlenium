class BaseEscalation:
    def __init__(self, name, status, **kwargs):
        self.name = name
        self.status = status
        self.attempt = kwargs.get("attempt", None)
        self.max_attempts = kwargs.get("max_attempts", None)
        self.last_check = kwargs.get("last_check", None)
        self.logs = kwargs.get("logs", None)
        self.args = kwargs.get("args", {})

    def run(self):
        pass
