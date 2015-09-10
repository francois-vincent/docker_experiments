# encoding: utf-8

import logging
import sys

import docker

import DIM, utils


def get_stdout_logger(log_level, name=__name__):
    log = logging.getLogger(name)
    out_hdlr = logging.StreamHandler(sys.stdout)
    out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    out_hdlr.setLevel(log_level)
    log.addHandler(out_hdlr)
    log.setLevel(log_level)

DIM.log = get_stdout_logger(logging.DEBUG)
utils.docker_client = DIM.docker_client = docker.Client(base_url='unix://var/run/docker.sock', version='auto')
