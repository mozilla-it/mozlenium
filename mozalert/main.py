#!/usr/bin/env python

import sys
from kubernetes import client, config, watch
import os
import logging

from mozalert.state import State, Status
from mozalert.check import Check

# kubernetes.client.rest.ApiException

def main():
    """
    the main thread watches the api server event stream for our crd objects and process
    events as they come in. Each event has an associated operation:

    ADDED: a new check has been created. the main thread creates a new check object which
           creates a threading.Timer set to the check_interval.

    DELETED: a check has been removed. Cancel/resolve any running threads and delete the
             check object.

    MODIFIED: this can be triggered by the user patching their check, or by a check thread
              updating the object status. NOTE: updating the status subresource SHOULD NOT
              trigger a modify, this is probably a bug in k8s. when a check is updated the
              changes are applied to the check object.

    ERROR: this can occur sometimes when the CRD is changed; it causes the process to die
           and restart.

    """
    logging.basicConfig(
        format="[%(asctime)s] %(name)s [%(levelname)s]: %(message)s", level=logging.INFO
    )

    if "KUBERNETES_PORT" in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()

    configuration = client.Configuration()
    configuration.assert_hostname = False

    api_client = client.api_client.ApiClient(configuration=configuration)
    batch_v1 = client.BatchV1Api()
    core_v1 = client.CoreV1Api()
    crd_client = client.CustomObjectsApi(api_client)

    clients = {"client": batch_v1, "pod_client": core_v1, "crd_client": crd_client}

    logging.info("Waiting for Controller to come up...")
    resource_version = ""
    threads = {}
    while True:
        stream = watch.Watch().stream(
            crd_client.list_cluster_custom_object,
            "crd.k8s.afrank.local",
            "v1",
            "checks",
            resource_version=resource_version,
        )
        for event in stream:
            obj = event.get("object")
            operation = event.get("type")
            logging.info(operation)
            if operation == "ERROR":
                logging.info("Received ERROR operation, Dying.")
                return 2
            if operation not in ["ADDED", "MODIFIED", "DELETED"]:
                logging.info(f"Received unexpected operation {operation}. Moving on.")
                continue

            spec = obj.get("spec")
            intervals = {
                "check_interval": spec.get("check_interval"),
                "retry_interval": spec.get("retry_interval", ""),
                "notification_interval": spec.get("notification_interval", ""),
            }
            metadata = obj.get("metadata")
            annotations = metadata.get("annotations", {})
            name = metadata.get("name")
            namespace = metadata.get("namespace")
            thread_name = f"{namespace}/{name}"

            # when we restart the stream start from events after this version
            resource_version = metadata.get("resourceVersion")
            
            pod_template = spec.get("template", {})
            pod_spec = pod_template.get("spec", {})

            if operation == "ADDED":
                threads[thread_name] = Check(
                    name=name,
                    namespace=namespace,
                    spec=pod_spec,
                    **clients,
                    **intervals,
                )
            elif operation == "DELETED":
                if thread_name in threads:
                    threads[thread_name].shutdown()
                    del threads[thread_name]
            elif operation == "MODIFIED":
                logging.info(f"Detected a modification to {thread_name}")
                threads[thread_name].update(name=name,namespace=namespace,spec=pod_spec,**clients,**intervals)

if __name__ == "__main__":
    sys.exit(main())
