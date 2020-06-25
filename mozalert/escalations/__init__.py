class BaseEscalation:
    def __init__(self, name, status, **kwargs):
        self.name = name
        self.status = status
        self.attempt = kwargs.get("attempt", None)
        self.max_attempts = kwargs.get("max_attempts", None)
        self.last_check = kwargs.get("last_check", None)
        self.logs = kwargs.get("logs", None)
        self.args = kwargs.get("args", {})
        self.message = f"""
            <p>
            <b>Name:</b> {self.name}<br>
            <b>Status:</b> {self.status}<br>
            """
        if self.attempt and self.max_attempts:
            self.message += (
                "\n" + f"<b>Attempt:</b> {self.attempt}/{self.max_attempts}<br>"
            )
        elif self.attempt:
            self.message += "\n" + f"<b>Attempt:</b> {self.attempt}<br>"
        if self.last_check:
            self.message += "\n" + f"<b>Last Check:</b> {self.last_check}<br>"
        if self.logs:
            self.message += (
                "\n" + f"<b>More Details:</b><br> <pre>{self.logs}</pre><br>"
            )
        self.message += "\n" + "</p>"
        self.subject = f"Mozalert {self.status}: {self.name}"

    def run(self):
        pass
