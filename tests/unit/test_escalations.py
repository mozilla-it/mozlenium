import unittest
import unittest.mock as mock
import os

from mozalert.events import event

from tests import events


class TestEscalations(unittest.TestCase):
    def test_escalation_parser(self):
        event_blob = events.add_event
        event_blob["object"]["spec"]["escalations"] = []
        esc = {"type": "email", "args": {"email": "afrank@mozilla.com"}}

        event_blob["object"]["spec"]["escalations"] += [esc]

        # test to be sure "normal" escalation parsing works
        evt = event.Event(**event_blob)

        test_key = "MY_EMAIL"
        test_email = "afrank+env@mozilla.com"

        os.environ[test_key] = test_email

        env_esc = {"type": "email", "env_args": {"email": test_key}}

        event_blob["object"]["spec"]["escalations"] += [env_esc]

        # this time we should have two escalations and one of them should be
        # for afrank+env@mozilla.com
        evt = event.Event(**event_blob)

        assert len(evt.config.escalations) == 2, "Wrong number of escalations!"

        assert (
            evt.config.escalations[1]["args"]["email"] == test_email
        ), "env_args were not parsed correctly!"
