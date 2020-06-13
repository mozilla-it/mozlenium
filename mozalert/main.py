#!/usr/bin/env python

import sys
import logging

from mozalert.controller import Controller

logging.basicConfig(
    format="[%(asctime)s] %(name)s [%(levelname)s]: %(message)s", level=logging.INFO
)


def main():
    Controller().run()


if __name__ == "__main__":
    sys.exit(main())
