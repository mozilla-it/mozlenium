from mozalert.escalations import BaseEscalation

from urllib.parse import urlencode, quote_plus

import os

import requests
import json


class Escalation(BaseEscalation):
    def __init__(self, name, status, config, args):
        super().__init__(name, status, config, args)
        self.webhook_url = self.args.get("webhook_url")
        self.channel = self.args.get("channel")
        gcp_project = os.environ.get("GCP_PROJECT", None)
        gcp_cluster = os.environ.get("GCP_CLUSTER", None)
        gcp_region = os.environ.get("GCP_REGION", None)
        more_details = []

        more_details += [self.status.message]

        if gcp_project:
            _gcp_logs_args = { "project": gcp_project, "advancedFilter": f"logName=projects/{gcp_project}/logs/{self.config.name}" }
            gcp_logs_args = urlencode(_gcp_logs_args, quote_via=quote_plus)
            gcp_logs_url = f"https://console.cloud.google.com/logs/viewer?{gcp_logs_args}"
            more_details += [f"<{gcp_logs_url}|view logs>"]

        if gcp_project and gcp_region and gcp_cluster:
            gcp_workload_url = f"https://console.cloud.google.com/kubernetes/job/{gcp_region}/{gcp_project}/{gcp_cluster}/{self.config.name}/details?project={gcp_project}"
            more_details += [f"<{gcp_workload_url}|GCP>"]

        if self.config.check_url:
            more_details += [f"<{self.config.check_url}|view failed url>"]

        color = "#ff0000"  # red
        if self.status.status.name == "OK":
            color = "#36a64f"  # green
        
        more_details_flat = "\n".join(more_details)

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
                        {"title": "Status", "value": self.status.status.name, "short": True},
                        {"title": "Attempt", "value": self.status.attempt, "short": True},
                        {"title": "More Details", "value": f"{more_details_flat}", "short": False},
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
