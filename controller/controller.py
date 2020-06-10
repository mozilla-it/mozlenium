#!/usr/bin/env python

import sys
import json
import yaml
from kubernetes import client, config, watch
import os
import logging
from enum import Enum
import threading
from time import sleep
#from types import SimpleNamespace
import datetime
import pytz

# kubernetes.client.rest.ApiException

class State(Enum):
    OK = 0
    WARN = 1
    CRITICAL = 2
    UNKNOWN = 3
    RETRY = 4
    RUNNING = 5
    NEW = 6

class Check:
    def __init__(self,**kwargs):
        self._name = kwargs.get("name")
        self._namespace = kwargs.get("namespace")
        self._spec = kwargs.get("spec")
        self._check_interval = float(kwargs.get("check_interval"))
        self._retry_interval = float(kwargs.get("retry_interval",0))
        self._notification_interval = float(kwargs.get("notification_interval",0))

        self._max_attempts = int(kwargs.get("max_attempts","3"))
        self._attempt = 0
        self._next_check = None

        self._state = State.NEW
        self._pending = False

        self.client = kwargs.get("client", client.BatchV1Api())
        self.pod_client = kwargs.get("pod_client", client.CoreV1Api())
        self.crd_client = kwargs.get("crd_client", client.CustomObjectsApi())

        self.thread = None

        if not self._retry_interval:
            self._retry_interval = self._check_interval
        if not self._notification_interval:
            self._notification_interval = self._check_interval
        
        self._check_interval *= 60
        self._retry_interval *= 60
        self._notification_interval *= 60

        self._next_interval = self._check_interval
        
        self.set_crd_status()
        self.start()

    @property
    def name(self):
        return self._name
    @property
    def namespace(self):
        return self._namespace
    @property
    def spec(self):
        return self._spec
    def __repr__(self):
        return f"{self._namespace}/{self._name}"
    def shutdown(self):
        self.stop_thread()
        self.delete_job()
    def check(self):
        """
        main thread for creating then watching a check job
        """
        logging.info(f"Running the check thread instance for {self._namespace}/{self._name}")
        self._attempt += 1
        self.run_job()
        logging.info(f"Check finished for {self._namespace}/{self._name}")
        logging.info(f"Cleaning up finished job for {self._namespace}/{self._name}")
        self.delete_job()
        if self._state == State.OK:
            self._attempt = 0
            self._next_inteval = self._check_interval
        elif self._attempt >= self._max_attempts:
            # do the escalation
            logging.info("Escalating {self._namespace}/{self._name}")
            self._next_interval = self._retry_interval # TODO keep retrying after escalation? giveup? reset?
        else:
            # not state OK and not enough failures to escalate
            self._next_interval = self._retry_interval
        self._next_check = str(pytz.utc.localize(datetime.datetime.utcnow()) + datetime.timedelta(seconds=self._next_interval))
        self.set_crd_status()
        self.start()
    def start(self):
        logging.info(f"Starting check thread for {self._namespace}/{self._name} at interval {self._next_interval}")
        self.thread = threading.Timer(self._next_interval,self.check)
        self.thread.setName(f"{self._namespace}/{self._name}")
        self.thread.start()
    def stop_thread(self):
        logging.info(f"Stopping check thread for {self._namespace}/{self._name}")
        self.thread.cancel()
        self.thread.join()
    def run_job(self): 
        logging.info(f"Running job for {self._namespace}/{self._name}")
        self._pending = True
        pod_spec = client.V1PodSpec(**self._spec)
        template = client.V1PodTemplateSpec(metadata=client.V1ObjectMeta(labels={"app": self._name}),spec=pod_spec)
        job_spec = client.V1JobSpec(template=template,backoff_limit=0) # ttl_seconds_after_finished
        job = client.V1Job(api_version="batch/v1",kind="Job",metadata=client.V1ObjectMeta(name=self._name),spec=job_spec)
        try:
            #api_response = batch_v1.patch_namespaced_job(name, namespace, body=job)
            api_response = batch_v1.create_namespaced_job(body=job,namespace=self._namespace)
            logging.info(f"Job created for {self._namespace}/{self._name}")
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)
        while True:
            status,runtime = self.get_job_status()
            #logging.info(status)
            #logging.info(self._pending)
            if self._pending and status != State.UNKNOWN:
                self._pending = False
            if status in [ State.OK, State.CRITICAL, State.UNKNOWN ] and not self._pending:
                self._state = status
                for log_line in self.get_job_logs().split('\n'):
                    logging.info(log_line)
                break
            sleep(3)
        logging.info(f"Job finished for {self._namespace}/{self._name} in {runtime} seconds with status {self._state}")
    def get_job_logs(self):
        api_response = self.pod_client.list_namespaced_pod(namespace=self._namespace, label_selector=f"app={self._name}")
        logs = ""
        for pod in api_response.items:
            logs += self.pod_client.read_namespaced_pod_log(pod.metadata.name,self._namespace)
        return logs

    def get_job_status(self):
        """
        {'active': 1,
         'completion_time': None,
         'conditions': None,
         'failed': None,
         'start_time': datetime.datetime(2020, 6, 5, 4, 13, 11, tzinfo=tzlocal()),
         'succeeded': None}
        """
        runtime = -1
        try:
            api_response = self.client.read_namespaced_job_status(self._name, self._namespace)
            if api_response.status.start_time:
                runtime = datetime.datetime.now() - api_response.status.start_time.replace(tzinfo=None)
            if api_response.status.succeeded:
                return (State.OK,runtime)
            if api_response.status.failed:
                #logging.info(api_response.status)
                return (State.CRITICAL,runtime)
            if api_response.status.active==1:
                return (State.RUNNING,runtime)
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)
        return (State.UNKNOWN,runtime)
    def set_crd_status(self):
        now = str(pytz.utc.localize(datetime.datetime.utcnow()))

        merge = { 
            "spec": { 
                "_status": str(self._state.name), 
                "_attempt": f"{self._attempt}/{self._max_attempts}",
                "_lastCheckTimestamp":  now,
                "_nextCheckTimestamp": self._next_check,
            } 
        }

        try:
            api_response = self.crd_client.patch_namespaced_custom_object("crd.k8s.afrank.local", "v1", self._namespace, "checks", self._name, body=merge)
            print(api_response)
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)

    def delete_job(self):
        try:
            api_response = self.client.delete_namespaced_job(self._name, self._namespace, propagation_policy='Foreground')
        except Exception as e:
            logging.info(sys.exc_info()[0])
            logging.info(e)

if __name__ == "__main__":
    logging.basicConfig(format="[%(asctime)s] %(name)s [%(levelname)s]: %(message)s", level=logging.INFO)

    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()

    configuration = client.Configuration()
    configuration.assert_hostname = False

    api_client = client.api_client.ApiClient(configuration=configuration)
    batch_v1 = client.BatchV1Api()
    core_v1 = client.CoreV1Api()
    crd_client = client.CustomObjectsApi(api_client)

    print(crd_client.list_cluster_custom_object("crd.k8s.afrank.local","v1","checks"))

    logging.info("Waiting for Controller to come up...")
    resource_version = ''
    threads = {}
    while True:
        stream = watch.Watch().stream(crd_client.list_cluster_custom_object, "crd.k8s.afrank.local", "v1", "checks", resource_version=resource_version)
        for event in stream:
            obj = event.get("object")
            #logging.info(obj)
            operation = event.get("type")
            logging.info(operation)
            if operation not in [ "ADDED", "MODIFIED", "DELETED" ]:
                logging.info(f"Received unexpected operation {operation}. Moving on.")
                continue

            spec = obj.get("spec")
            intervals = {
                "check_interval": spec.get("check_interval"),
                "retry_interval": spec.get("retry_interval",""),
                "notification_interval": spec.get("notification_interval","")
            }
            metadata = obj.get("metadata")
            name = metadata.get("name")
            namespace = metadata.get("namespace")
            thread_name = f"{namespace}/{name}"
            resource_version = metadata.get("resourceVersion")
            pod_template = spec.get("template",{})
            pod_spec = pod_template.get("spec",{})

            if operation == "ADDED":
                threads[thread_name] = Check(name=name,namespace=namespace,spec=pod_spec,client=batch_v1,pod_client=core_v1,crd_client=crd_client,**intervals)
            elif operation == "DELETED":
                if thread_name in threads:
                    threads[thread_name].shutdown()
                    del threads[thread_name]
            elif operation == "MODIFIED":
                logging.info(f"Detected a modification to {thread_name}")
