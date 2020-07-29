import datetime

add_event = {
    "type": "ADDED",
    "object": {
        "kind": "Check",
        "metadata": {
            "name": "test-add-event",
            "namespace": "default",
            "resourceVersion": "1",
        },
        "spec": {
            "check_cm": "check-test-login-cm",
            "check_interval": "1m",
            "escalations": [{"args": {"email": "afrank@mozilla.com"}, "type": "email"}],
            "image": "afrank/mozlenium",
            "max_attempts": 25,
            "notification_interval": "10m",
            "retry_interval": "1m",
            "secret_ref": "check-test-login-secrets",
        },
        "status": {},
    },
    "raw_object": {},
}

re_add_event = {
    "type": "ADDED",
    "object": {
        "kind": "Check",
        "metadata": {
            "name": "test-re-add-event",
            "namespace": "default",
            "resourceVersion": "1",
        },
        "spec": {
            "check_cm": "check-test-login-cm",
            "check_interval": "10m",
            "escalations": [{"args": {"email": "afrank@mozilla.com"}, "type": "email"}],
            "image": "afrank/mozlenium",
            "max_attempts": 25,
            "notification_interval": "10m",
            "retry_interval": "1m",
            "secret_ref": "check-test-login-secrets",
        },
        "status": {
            "attempt": "0",
            "last_check": "None",
            "logs": "",
            "next_check": str(datetime.datetime.utcnow()).split(".")[0],
            "state": "IDLE",
            "status": "OK",
        },
    },
    "raw_object": {},
}
