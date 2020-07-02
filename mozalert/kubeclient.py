import os

from kubernetes import client, config, watch

from kubernetes.client.rest import ApiException


class KubeClient:
    """
    Set up the various clients we will need
    for talking to kubernetes
    """

    def __init__(self):
        if "KUBERNETES_PORT" in os.environ:
            config.load_incluster_config()
        else:
            config.load_kube_config()

        self._client_config = client.Configuration()
        self._client_config.assert_hostname = False

        self._api_client = client.api_client.ApiClient(
            configuration=self._client_config
        )

        self._BatchV1Api = client.BatchV1Api()
        self._CoreV1Api = client.CoreV1Api()
        self._CustomObjectsApi = client.CustomObjectsApi(self._api_client)

    @property
    def BatchV1Api(self):
        return self._BatchV1Api

    @property
    def CoreV1Api(self):
        return self._CoreV1Api

    @property
    def CustomObjectsApi(self):
        return self._CustomObjectsApi

    @staticmethod
    def make_job(name, **kwargs):
        """
        The k8s resources take the form:
            pod spec -> pod template -> job spec -> job

        """
        pod_spec = client.V1PodSpec(**kwargs)
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}), spec=pod_spec,
        )
        job_spec = client.V1JobSpec(template=template, backoff_limit=0)
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=name),
            spec=job_spec,
        )
        return job

    @staticmethod
    def Watch(*args, **kwargs):
        return watch.Watch(*args, **kwargs)
