from mozalert.escalations import BaseEscalation

import os
from mozalert.utils.sendgrid import SendGridTools


class Escalation(BaseEscalation):
    def __init__(self, name, status, **kwargs):
        super().__init__(name, status, **kwargs)
        self.email = self.args.get("email")
        self.api_key = os.environ.get("SENDGRID_API_KEY", "")
        self.from_email = "Mozalert <afrank+mozalert@mozilla.com>"
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
        SendGridTools.send_message(
            api_key=self.api_key,
            to_emails=[self.email],
            from_email=self.from_email,
            message=self.message,
            subject=self.subject,
        )
