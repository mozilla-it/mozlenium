from mozalert.escalations import BaseEscalation

import os
from mozalert.utils.sendgrid import SendGridTools


class Escalation(BaseEscalation):
    def __init__(self, name, status, **kwargs):
        super().__init__(name, status, **kwargs)
        self.email = self.args.get("email")
        self.api_key = os.environ.get("SENDGRID_API_KEY", "")
        self.from_email = "Mozalert <afrank+mozalert@mozilla.com>"

    def run(self):
        SendGridTools.send_message(
            api_key=self.api_key,
            to_emails=[self.email],
            from_email=self.from_email,
            message=self.message,
            subject=self.subject,
        )
