# encoding: utf-8

import logging
import sys

import DIM

log_level = logging.DEBUG

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(log_level)
log.addHandler(out_hdlr)
log.setLevel(log_level)

DIM.log = log