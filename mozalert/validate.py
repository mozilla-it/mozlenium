#!/usr/bin/env python

import sys
import logging

from mozalert import kubeclient

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s", level=logging.INFO
)


class Validator:
    """
    This is a separate entrypoint for mozalert,
    called mozalert-validator. The purpose is to,
    instead of running mozalert, check to be sure mozalert
    is currently running and installed correctly.
    """
    def __init__(self, domain, version, plural):
        self.domain = domain
        self.version = version
        self.plural = plural
        self.kube = kubeclient.KubeClient()

    def run(self):
        if not self.validate_crd():
            raise Exception("Failed to validate CRD")

    def validate_crd(self):
        try:
            check_list = self.kube.CustomObjectsApi.list_cluster_custom_object(
                self.domain, self.version, self.plural, watch=False
            )
        except Exception as e:
            logging.error(e)
            logging.error(sys.exc_info()[0])
            return False
        return True

def main():
    return Validator(*sys.argv[1:]).run()

if __name__ == "__main__":
    sys.exit(main())
