from mozalert.escalations import BaseEscalation

import os

import requests
import json


class Escalation(BaseEscalation):
    def __init__(self, name, status, **kwargs):
        super().__init__(name, status, **kwargs)
        self.webhook_url = self.args.get("webhook_url")
        self.channel = self.args.get("channel")
        color = "#ff0000"  # red
        if status == "OK":
            color = "#36a64f"  # green
        self.slack_message = {
            "channel": self.channel,
            "username": "Mozalert",
            "icon_emoji": ":scream_cat:",
            "attachments": [
                {
                    "mrkdwn_in": ["text"],
                    "color": color,
                    "fields": [
                        {"title": "Target", "value": name, "short": False},
                        {"title": "Status", "value": status, "short": True},
                        {"title": "Attempt", "value": self.attempt, "short": True},
                    ],
                }
            ],
        }
        self.slack_message = json.dumps(self.slack_message)

    def run(self):
        resp = requests.post(
            self.webhook_url,
            data=self.slack_message,
            headers={"Content-Type": "application/json"},
        )
