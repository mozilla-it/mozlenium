from mozalert.escalations import BaseEscalation

import os
from mozalert.utils.sendgrid import SendGridTools


class Escalation(BaseEscalation):
    def __init__(self, name, status, config, args):
        super().__init__(name, status, config, args)
        self.email = self.args.get("email")
        self.api_key = os.environ.get("SENDGRID_API_KEY", "")
        self.from_email = "Mozalert <afrank+mozalert@mozilla.com>"
        self.message = f"""
            <p>
            <b>Name:</b> {self.name}<br>
            <b>Status:</b> {self.status.status.name}<br>
            """
        if self.status.attempt and self.config.max_attempts:
            self.message += (
                "\n"
                + f"<b>Attempt:</b> {self.status.attempt}/{self.config.max_attempts}<br>"
            )
        elif self.status.attempt:
            self.message += "\n" + f"<b>Attempt:</b> {self.status.attempt}<br>"
        if self.status.last_check:
            self.message += "\n" + f"<b>Last Check:</b> {self.status.last_check}<br>"
        if self.status.logs:
            self.message += (
                "\n" + f"<b>More Details:</b><br> <pre>{self.status.logs}</pre><br>"
            )

        # When we find another thing to reference, we should generalize this line.  As is we are only
        # going to pass the source code reference to email.
        if self.config.references:
            if self.config.references.source_code:
                self.message += (
                    "\n"
                    + f"<b>Source Code for Check:</b><br> <pre>{self.config.references.source_code}</pre><br>"
                )

        self.message += "\n" + "</p>"
        self.subject = f"Mozalert {self.status.status.name}: {self.name}"

    def run(self):
        SendGridTools.send_message(
            api_key=self.api_key,
            to_emails=[self.email],
            from_email=self.from_email,
            message=self.message,
            subject=self.subject,
        )
