# encoding: utf-8

from __future__ import unicode_literals, print_function
from io import BytesIO
import random

import docker

docker_client = docker.Client(base_url='unix://var/run/docker.sock', version='auto')


def wait(iterable):
    for line in iterable:
        log.debug(line)
        if line.startswith(b'{"errorDetail'):
            raise RuntimeError("Build failed @" + line)


def random_hex(len=32):
    return ''.join(random.choice('0123456789abcdef') for _ in xrange(len))


def render(string, cont):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return string.format(cont)


class DockerRunParameters(object):
    """
    A class to define parameters for the docker create/run commands.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class DockerImageManager(object):
    """
    A class to manage Docker images, wich features:
    - Create a new image out of a Dockerfile that can be inline or file,
      raw or template.
    - Run an image with a set of parameters.
    - Commit a container.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if not self.dockerfile_string and not self.dockerfile_name and not self.image_name:
            raise RuntimeError("You have to specify a Dockerfile "
                               "(dockerfile_string or dockerfile_name) or an image name")
        self.log = getattr(self, 'log', log)
        self.image_name = getattr(self, 'image_name', random_hex())
        self.log.debug("{}.__init__(image_name={})".format(self.__class__.__name__, self.image_name))

    def get_container_name(self):
        return getattr(self, 'container_name', self.image_name[:12] + '_' + random_hex(10))

    def get_dockerfile(self):
        if not self.dockerfile_string and not self.dockerfile_name:
            raise RuntimeError("You have to specify a Dockerfile (dockerfile_string or dockerfile_name)")
        if self.dockerfile_string:
            dockerfile = self.dockerfile_string
        else:
            with open(self.dockerfile_name, 'rb') as f:
                dockerfile = f.read()
        return BytesIO(render(dockerfile, getattr(self, 'dockerfile_variables', {})))

    def build(self):
        self.log.info("Building image {}".format(self.image_name))
        wait(docker_client.build(fileobj=self.get_dockerfile(), tag=self.image_name, rm=True))
        return self

    def run(self, parameters):
        pass
