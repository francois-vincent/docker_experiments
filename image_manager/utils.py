# encoding: utf-8

import collections
from contextlib import contextmanager, nested
import os
import random
import shutil
import tempfile

log = None

global_temp_im_dir = '/tmp/temp_im'
if not os.access(global_temp_im_dir, os.W_OK):
    os.mkdir(global_temp_im_dir, 0766)


def absjoin(*p):
    return os.path.abspath(os.path.join(*p))


@contextmanager
def temp_file(file_name, content, context):
    """
    Manages a temp file life cycle.
    The temp file content can be rendered from a template.
    The context is enriched for nested tempfile
    :param content: content or template
    :param file_name: optional file name
    :param context: context if content is a template
    """
    path = None
    try:
        dir = tempfile.mkdtemp(dir=global_temp_im_dir)
        path = os.path.join(dir, file_name)
        log.debug("Create temp file {}".format(path))
        with open(path, 'w') as f:
            f.write(render(content, context))
        context[file_name] = path
        yield path
    finally:
        if path:
            log.debug("Remove temp file {}".format(path))
            del context[file_name]
            shutil.rmtree(dir, ignore_errors=True)


def chain_temp_files(files, context):
    return nested(*(temp_file(name, content, context) for name, content in files.iteritems()))


def render(string, context):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return string.format(**context)


def wait(iterable):
    if isinstance(iterable, (collections.Iterable, collections.Iterator)):
        for line in iterable:
            log.debug(line)
            if line.startswith(b'{"errorDetail'):
                raise RuntimeError("Build failed @" + line)


def random_hex(len=24):
    return ''.join(random.choice('0123456789abcdef') for _ in xrange(len))
