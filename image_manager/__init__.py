# encoding: utf-8

import logging
import sys

import DIM, utils


log_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
}

def get_stdout_logger(log_level, name=__name__):
    log = logging.getLogger(name)
    out_hdlr = logging.StreamHandler(sys.stdout)
    out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    out_hdlr.setLevel(log_level)
    log.addHandler(out_hdlr)
    log.setLevel(log_level)
    return log

utils.log = DIM.log = get_stdout_logger(logging.DEBUG)
