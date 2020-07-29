from types import SimpleNamespace


def fakecallable(*args, **kwargs):
    pass


def fake_job_status(*args, **kwargs):
    return SimpleNamespace(
        status=SimpleNamespace(
            active=False, succeeded=True, failed=False, start_time=None
        )
    )


def fake_pod_list(*args, **kwargs):
    return SimpleNamespace(items=[])


class FakeClient:
    CustomObjectsApi = SimpleNamespace(
        list_cluster_custom_object=fakecallable,
        patch_namespaced_custom_object_status=fakecallable,
    )
    BatchV1Api = SimpleNamespace(
        create_namespaced_job=fakecallable,
        read_namespaced_job_status=fake_job_status,
        delete_namespaced_job=fakecallable,
    )
    CoreV1Api = SimpleNamespace(
        list_namespaced_pod=fake_pod_list, read_namespaced_pod_log=fakecallable
    )

    def FakeStream(*args, **kwargs):
        return []

    def Watch(*args, **kwargs):
        return SimpleNamespace(stream=FakeClient.FakeStream)

    def make_job(*args, **kwargs):
        return None

    @property
    def domain(self):
        return "crd.k8s.afrank.local"

    @property
    def version(self):
        return "v1"

    @property
    def plural(self):
        return "checks"
