"""
Provide logger object.

Any other modules in "ajenga" should use "logger" from this module
to log messages.
"""

import os
import logging
import sys
import datetime

LOG_DIR: str = './logs'

log_dir = os.path.expanduser(LOG_DIR)
os.makedirs(log_dir, exist_ok=True)


def get_logger(name: str, fname: str = None):
    formatter = logging.Formatter('[%(asctime)s %(name)s] %(levelname)s: %(message)s')
    logger = logging.getLogger(name)
    while logger.hasHandlers():
        del logger.handlers[0]
    default_handler = logging.StreamHandler(sys.stdout)
    default_handler.setFormatter(formatter)
    error_handler = logging.FileHandler(
        os.path.join(log_dir, f'error-{fname if fname else name}.log'), encoding='utf8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    critical_handler = logging.FileHandler(
        os.path.join(log_dir, f'critical-{fname if fname else name}.log'), encoding='utf8')
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(formatter)
    logger.addHandler(default_handler)
    logger.addHandler(error_handler)
    logger.addHandler(critical_handler)
    logger.setLevel(logging.INFO)
    return logger


logger = get_logger('ajenga')
