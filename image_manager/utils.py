# encoding: utf-8

import collections
import random


def wait(iterable):
    if isinstance(iterable, (collections.Iterable, collections.Iterator)):
        for line in iterable:
            log.debug(line)
            if line.startswith(b'{"errorDetail'):
                raise RuntimeError("Build failed @" + line)


def random_hex(len=24):
    return ''.join(random.choice('0123456789abcdef') for _ in xrange(len))


def render(string, context):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return string.format(context)


class TransDict(dict):
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return key


def find_image(id=None, name=None):
    if id:
        for img in docker_client.images():
            if id == img['Id']:
                return img
    elif name:
        for img in docker_client.images():
            for t in img['RepoTags']:
                if t.split(':')[0] == name:
                    return img


def find_container(container=None, image=None, ignore_state=True):
    if container:
        for cont in docker_client.containers(all=ignore_state):
            if not image or cont['Image'].split(':')[0] == image:
                for name in cont['Names']:
                    if name[1:] == container:
                        return cont
    elif image:
        for cont in docker_client.containers(all=ignore_state):
            if cont['Image'].split(':')[0] == image:
                return cont
