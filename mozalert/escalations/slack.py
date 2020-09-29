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
        fields = []

        fields += [{"title": "Target", "value": name, "short": False}]
        fields += [{"title": "Status", "value": self.status.status.name, "short": True}]

        if self.config.labels:
            labels_flat = "\n".join(
                [f"{key}: {val}" for key, val in self.config.labels.items()]
            )
            fields += [{"title": "Labels", "value": labels_flat, "short": False}]

        fields += [{"title": "Attempt", "value": self.status.attempt, "short": True}]

        more_details += [self.status.message]

        if gcp_project:
            filter_list = [f"resource.labels.container_name={self.config.name}"]

            if gcp_region and gcp_cluster:
                filter_list.append(f"resource.labels.cluster_name={gcp_cluster}")
                filter_list.append(f"resource.labels.location={gcp_region}")

            advanced_filter = " ".join(filter_list)
            _gcp_logs_args = {
                "project": gcp_project,
                "advancedFilter": advanced_filter,
            }

            gcp_logs_args = urlencode(_gcp_logs_args, quote_via=quote_plus)
            gcp_logs_url = (
                f"https://console.cloud.google.com/logs/viewer?{gcp_logs_args}"
            )
            more_details += [f"<{gcp_logs_url}|view logs>"]

        if self.config.check_url:
            more_details += [f"<{self.config.check_url}|view failed url>"]

        color = "#ff0000"  # red
        if self.status.status.name == "OK":
            color = "#36a64f"  # green

        more_details_flat = "\n".join(more_details)

        fields += [
            {"title": "More Details", "value": more_details_flat, "short": False}
        ]

        self.slack_message = {
            "channel": self.channel,
            "username": "Mozalert",
            "icon_emoji": ":scream_cat:",
            "attachments": [
                {
                    "mrkdwn_in": ["text"],
                    "color": color,
                    "fields": fields,
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
