#!/usr/bin/env python

import sys
import logging
import signal

from mozalert.controller import Controller

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s", level=logging.INFO
)


class MainThread:
    def __init__(self):
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

        self.shutdown = False

        self.controller = Controller(shutdown=lambda: self.shutdown)
        self.controller.start()

    def terminate(self, signum=-1, frame=None):
        self.shutdown = True
        self.controller.terminate()

    def run(self):
        return self.controller.join()


def main():
    return MainThread().run()


if __name__ == "__main__":
    sys.exit(main())
