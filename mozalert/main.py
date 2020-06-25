#!/usr/bin/env python

import sys
import logging

from mozalert.controller import Controller

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s", level=logging.INFO
)


def main():
    return Controller().run()


if __name__ == "__main__":
    sys.exit(main())
