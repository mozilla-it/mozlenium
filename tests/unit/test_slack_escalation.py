import unittest
import unittest.mock as mock
from unittest.mock import patch, MagicMock
import json


from mozalert.escalations.slack import Escalation


class TestEscalations(unittest.TestCase):
    def setUp(self):
        self.statusMock = MagicMock(message="failed-test-message", attempt=3)
        # name is a special object im magicmock land, and so has to be set seperately
        self.statusMock.status.name = "OK"
        self.configMock = MagicMock(check_url="fake_url")
        self.configMock.name = "mock_config_name"
        self.argsMock = MagicMock()
        args_dict = {"channel": "test_channel", "webhook_url": "test_webhook"}
        self.argsMock.get = MagicMock(side_effect=(lambda x: args_dict[x]))
        with patch.dict("os.environ", {"GCP_PROJECT": "TEST_PROJECT"}):
            self.gcp_project_escalation = Escalation(
                "test-escalation", self.statusMock, self.configMock, self.argsMock
            )

        full_env_dict = {
            "GCP_PROJECT": "TEST_PROJECT",
            "GCP_CLUSTER": "TEST_CLUSTER",
            "GCP_REGION": "TEST_REGION",
        }

        with patch.dict("os.environ", full_env_dict):
            self.gcp_project_long_escalation = Escalation(
                "test-escalation", self.statusMock, self.configMock, self.argsMock
            )

    def test_slack_escalation_link(self):
        slack_message_obj = json.loads(self.gcp_project_escalation.slack_message)
        more_details = list(
            filter(
                lambda fields: fields["title"] == "More Details",
                slack_message_obj["attachments"][0]["fields"],
            )
        )[0]["value"]
        url = "https://console.cloud.google.com/logs/viewer?project=TEST_PROJECT&advancedFilter=resource.labels.container_name%3Dmock_config_name"
        self.assertIn(url, more_details)

    def test_slack_escalation_long_link(self):
        slack_message_obj = json.loads(self.gcp_project_long_escalation.slack_message)
        more_details = list(
            filter(
                lambda fields: fields["title"] == "More Details",
                slack_message_obj["attachments"][0]["fields"],
            )
        )[0]["value"]
        url = "https://console.cloud.google.com/logs/viewer?project=TEST_PROJECT&advancedFilter=resource.labels.container_name%3Dmock_config_name+resource.labels.cluster_name%3DTEST_CLUSTER+resource.labels.location%3DTEST_REGION"
        self.assertIn(url, more_details)
