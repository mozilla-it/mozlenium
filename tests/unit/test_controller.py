import unittest
import unittest.mock as mock
import logging
import datetime

import mozalert.kubeclient

from mozalert.controller import Controller

from time import sleep
from types import SimpleNamespace

from tests import events, fake

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s", level=logging.INFO
)


def fake_restart_stream(*args, **kwargs):
    if not kwargs.get("resource_version", ""):
        return [events.re_add_event]
    return []


def fake_stream(*args, **kwargs):
    if not kwargs.get("resource_version", ""):
        return [events.add_event]
    return []


class TestController(unittest.TestCase):
    @mock.patch.object(mozalert.kubeclient, "KubeClient")
    def test_controller_create_check(self, FakeKube):
        fake.FakeClient.FakeStream = fake_stream
        FakeKube.return_value = fake.FakeClient

        shutdown = False
        c = Controller(shutdown=lambda: shutdown)
        c.start()

        sleep(5)

        assert c.checks[
            "default/test-add-event"
        ].thread.is_alive(), "Could not find the thread"

        shutdown = True
        c.terminate()
        c.join()

    @mock.patch.object(mozalert.kubeclient, "KubeClient")
    def test_controller_create_re_check(self, FakeKube):
        fake.FakeClient.FakeStream = fake_restart_stream
        # the ADD event has an interval of 600 seconds so if we can
        # see a next_interval of < 600 we know the status was read
        events.re_add_event["object"]["status"]["next_check"] = str(
            datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
        ).split(".")[0]
        FakeKube.return_value = fake.FakeClient

        check_name = (
            events.re_add_event["object"]["metadata"]["namespace"]
            + "/"
            + events.re_add_event["object"]["metadata"]["name"]
        )

        shutdown = False
        c = Controller(shutdown=lambda: shutdown)
        c.start()

        sleep(5)

        assert c.checks[
            check_name
        ].thread.is_alive(), "Could not find the thread"

        assert (
            c.checks[check_name].next_interval < 100
        ), "next_interval not set correctly"

        shutdown = True
        c.terminate()
        c.join()
