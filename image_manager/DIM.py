# encoding: utf-8

from __future__ import unicode_literals, print_function
from io import BytesIO
import os

import docker
docker_client, log = None, None

from utils import *


class DockerRunParameters(dict):
    """
    A class to define parameters for the docker create/run commands.
    """

    def __init__(self, **options):
        dict.__init__(self)
        volumes = options.pop('volumes', None)
        ports = options.pop('ports', None)
        self.update(options)
        self.kwargs = {}
        self['volumes'] = set()
        self['ports'] = set()
        if volumes:
            for vol in volumes:
                self.add_volume(vol)
        if ports:
            for port in ports:
                self.add_port(port)
        self.finalize()

    def add_volume(self, vol):
        binds = self.kwargs.setdefault('binds', {})
        host, guest = vol.split(':', 1)
        # default mode is 'rw', you can specify 'ro' instead
        if ':' in guest:
            guest, mode = guest.split(':')
        else:
            mode = 'rw'
        host = os.path.abspath(os.path.expanduser(host))
        binds[host] = {'bind': guest, 'mode': mode}
        self['volumes'].add(guest)

    def add_port(self, port):
        port_bindings = self.kwargs.setdefault('port_bindings', {})
        if isinstance(port, basestring):
            if ':' in port:
                # TODO does not accept format host_ip:host_port:guest_port yet
                host, guest = port.rsplit(':', 1)
                guest = int(guest)
                port_bindings[guest] = int(host)
                self['ports'].add(guest)
            elif '-' in port:
                start, end = port.split('-')
                for p in xrange(int(start), int(end) + 1):
                    port_bindings[p] = None
                    self['ports'].add(p)
            else:
                port = int(port)
                port_bindings[port] = None
                self['ports'].add(port)
        else:
            port_bindings[port] = None
            self['ports'].add(port)

    def finalize(self):
        if self.kwargs:
            self['host_config'] = docker.utils.create_host_config(**self.kwargs)

    def __add__(self, other):
        res = dict(self)
        res.update(other)
        return res


class DockerImageManager(object):
    """
    A class to manage Docker images, wich features:
    - Create a new image out of a Dockerfile that can be inline or file,
      raw or template.
    - Run an image with a set of parameters.
    - Commit a container.
    Each instance can manage a single image.
    """

    def __init__(self, **kwargs):
        kwargs['image'] = self.image_name = kwargs.pop('image_name', random_hex())
        self.log = kwargs.pop('log', log)
        self.dockerfile_string = kwargs.pop('dockerfile_string', None)
        self.dockerfile_name = kwargs.pop('dockerfile_name', None)
        if self.dockerfile_name:
            self.dockerfile_name = os.path.abspath(os.path.expanduser(self.dockerfile_name))
        self.log.debug("New {}(image_name='{}')".format(self.__class__.__name__, self.image_name))
        self.parameters = DockerRunParameters(**kwargs)

    def get_dockerfile(self):
        """ Docker file is pecified either via a string or a file.
            Then it is rendered according to an optional context (dictionary).
        """
        if not self.dockerfile_string and not self.dockerfile_name:
            raise RuntimeError("You have to specify a Dockerfile (dockerfile_string or dockerfile_name)")
        if self.dockerfile_string:
            dockerfile = self.dockerfile_string
        else:
            with open(self.dockerfile_name, 'rb') as f:
                dockerfile = f.read()
        return BytesIO(render(dockerfile, getattr(self, 'dockerfile_variables', {})))

    def pull(self, tag=None):
        if tag:
            docker_client.pull(self.image_name, tag)
        else:
            docker_client.pull(self.image_name)
        return self

    def build(self):
        self.log.info("Building image {}".format(self.image_name))
        wait(docker_client.build(fileobj=self.get_dockerfile(), tag=self.image_name, rm=True))
        return self

    def push(self, image_name=None, tag=None):
        image_name = image_name or self.image_name
        if tag:
            self.log.info("Pushing image '{}:{}'".format(image_name, tag))
            docker_client.push(image_name, tag)
        else:
            self.log.info("Pushing image '{}'".format(image_name))
            docker_client.push(image_name)
        return self

    def inspect(self):
        return docker_client.inspect_image(image_id=self.image_name)

    def remove_image(self, image_name=None):
        image_name = image_name or self.image_name
        try:
            docker_client.remove_image(image=image_name)
            self.log.info("Removing image '{}'".format(image_name))
        except docker.errors.APIError:
            self.log.warning("Can't remove image '{}': not found".format(image_name))
        return self

    def get_container(self, container_name=None):
        return DockerContainerManager(self, container_name)

    def create_container(self, container_name=None, start=True):
        return DockerContainerManager(self, container_name).create_container(start)


class DockerContainerManager(object):
    """
    A class to manage docker containers
    """
    def __init__(self, image, **kwargs):
        self.image = image
        self.image_name = image.image_name
        kwargs['name'] = self.container_name = kwargs.pop('container_name', self.image_name[:12] + '_' + random_hex(10))
        self.parameters = self.image.parameters + kwargs

    def create(self, start=True):
        if find_container(container=self.container_name):
            raise RuntimeError("Container '{}' already exists".format(self.container_name))
        else:
            parameters = self.image.parameters + self.parameters
            try:
                docker_client.create_container(**parameters)
            except docker.errors.APIError:
                self.image.pull()
                docker_client.create_container(**parameters)
            if start:
                self.start()
        return self

    def start(self):
        docker_client.start(self.container_name)
        return self

    def inspect(self, field='NetworkSettings.IPAddress'):
        config = docker_client.inspect_container(self.container_name)
        if field:
            for x in field.split('.'):
                if x:
                    config = config.get(x)
        return config

    def exec_container(self, cmd):
        id = docker_client.exec_create(self.container_name, cmd, stdout=False, stdin=False)
        docker_client.exec_start(execid=id, detach=True)
        return self

    def copy_from_container(self, path):
        return docker_client.copy(self.container_name, path)

    def stop(self):
        docker_client.stop(self.container_name)
        return self

    def commit(self, image_name):
        docker_client.commit(self.container_name, image_name)
        return self

    def remove_container(self):
        docker_client.remove_container(self.container_name)
        return self
