import logging 

class CheckConfig:
    """
    the CheckConfig is used by Check objects as well as Event objects.

    The idea is when an event comes in it parses the config and compares it
    to the config of the running thread, and if there are differences it'll
    start a new thread.
    """
    def __init__(self,**kwargs):
        self._name=kwargs.get("name")
        self._namespace=kwargs.get("namespace")
        
        self._check_interval=float(kwargs.get("check_interval"))

        self._retry_interval=float(kwargs.get("retry_interval", 0))
        self._notification_interval=float(kwargs.get("notification_interval", 0))
        self._escalations=kwargs.get("escalations", [])
        self._max_attempts=int(kwargs.get("max_attempts", "3"))
        self._timeout=float(kwargs.get("timeout", 0))
        
        self.pod_spec = kwargs.get("pod_spec",{})

        if not self.retry_interval:
            self._retry_interval = self.check_interval

        if not self.notification_interval:
            self._notification_interval = self.check_interval

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace
    
    @property
    def check_interval(self):
        return self._check_interval
    
    @property
    def retry_interval(self):
        return self._retry_interval
    
    @property
    def notification_interval(self):
        return self._notification_interval
    
    @property
    def escalations(self):
        return self._escalations
    
    @property
    def max_attempts(self):
        return self._max_attempts
    
    @property
    def timeout(self):
        return self._timeout

    @property
    def pod_spec(self):
        return self._pod_spec

    @pod_spec.setter
    def pod_spec(self,pod_spec):
        self._pod_spec = pod_spec

    def __iter__(self):
        return iter([
            ("name",self.name),
            ("namespace",self.namespace),
            ("check_interval",self.check_interval),
            ("retry_interval",self.retry_interval),
            ("notification_interval",self.notification_interval),
            ("escalations",self.escalations),
            ("max_attempts",self.max_attempts),
            ("timeout",self.timeout),
            ("pod_spec",self.pod_spec),
        ])

    def build_pod_spec(self, **kwargs):
        """
        generates a pod_spec dictionary from a set of parameters
        """
        secret_ref = kwargs.get("secret_ref", None)
        check_cm = kwargs.get("check_cm", None)
        check_url = kwargs.get("check_url", None)
        image = kwargs.get("image", None)
        args = kwargs.get("args", [])
        template = {
            "restart_policy": "Never",
            "containers": [{"name": self.name, "image": image}],
        }   
        if secret_ref:
            template["containers"][0]["envFrom"] = [{"secretRef": {"name": secret_ref}}]
        if check_cm:
            # TODO this seems problematic
            template["containers"][0]["volumeMounts"] = [
                {"name": "checks", "mountPath": "/checks", "readOnly": True}
            ]
            template["volumes"] = [{"name": "checks", "configMap": {"name": check_cm}}]
        if check_url:
            template["containers"][0]["args"] = [check_url]
        elif args:
            template["containers"][0]["args"] = args
        
        self.pod_spec = template
