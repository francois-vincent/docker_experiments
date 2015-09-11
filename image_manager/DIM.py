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
    allowed = ()

    def __init__(self, **options):
        dict.__init__(self)
        volumes = options.pop('volumes', None)
        ports = options.pop('ports', None)
        self.update(options)
        self.kwargs = {}
        if volumes:
            for vol in volumes:
                self.add_volume(vol)
        if ports:
            for port in ports:
                self.add_port(port)
        self.finalize()

    def add_volume(self, vol):
        binds = self.kwargs.setdefault('binds', {})
        volumes = self.setdefault('volumes', set())
        host, guest = vol.split(':', 1)
        # default mode is 'rw', you can specify 'ro' instead
        if ':' in guest:
            guest, mode = guest.split(':')
        else:
            mode = 'rw'
        host = os.path.abspath(os.path.expanduser(host))
        binds[host] = {'bind': guest, 'mode': mode}
        volumes.add(guest)

    def add_port(self, port):
        port_bindings = self.kwargs.setdefault('port_bindings', {})
        ports = self.setdefault('ports', set())
        if isinstance(port, basestring):
            if ':' in port:
                # TODO does not accept format host_ip:host_port:guest_port yet
                host, guest = port.rsplit(':', 1)
                guest = int(guest)
                port_bindings[guest] = int(host)
                ports.add(guest)
            elif '-' in port:
                start, end = port.split('-')
                for p in xrange(int(start), int(end) + 1):
                    port_bindings[p] = None
                    ports.add(p)
            else:
                port = int(port)
                port_bindings[port] = None
                ports.add(port)
        else:
            port_bindings[port] = None
            ports.add(port)

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
        self.parameters = DockerRunParameters(**kwargs)
        self.log.debug("New {}(image_name='{}')".format(self.__class__.__name__, self.image_name))

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
        return DockerContainerManager(self, container_name=container_name)

    def create_container(self, container_name=None, start=True):
        return DockerContainerManager(self, container_name=container_name).create(start)


class DockerContainerManager(object):
    """
    A class to manage docker containers
    """
    def __init__(self, image, **kwargs):
        self.image = image
        self.image_name = image.image_name
        self.log = image.log
        kwargs['name'] = self.container_name = kwargs.pop('container_name', self.random_name())
        self.parameters = self.image.parameters + kwargs
        self.log.debug("New {}(container_name='{}')".format(self.__class__.__name__, self.container_name))

    def random_name(self):
        return self.image_name[:12] + '_' + random_hex(11)

    @property
    def exists(self):
        return bool(self.inspect('State.Running'))

    @property
    def is_running(self):
        return self.inspect('State.Running') == 'true'

    def create(self, start=True, allow_existing=False):
        if self.exists and not allow_existing:
            raise RuntimeError("Container '{}' already exists".format(self.container_name))
        else:
            parameters = self.image.parameters + self.parameters
            try:
                docker_client.create_container(**parameters)
            except docker.errors.APIError:
                self.image.pull()
                docker_client.create_container(**parameters)
        if start and not self.is_running:
            self.start()
        return self

    def start(self):
        docker_client.start(self.container_name)
        return self

    def inspect(self, field='NetworkSettings.IPAddress', container_name=None):
        try:
            config = docker_client.inspect_container(container_name or self.container_name)
            if field:
                for x in field.split('.'):
                    if x:
                        config = config.get(x)
            return config
        except docker.errors.NotFound:
            return None

    def exec_container(self, cmd, wait=True):
        id = docker_client.exec_create(self.container_name, cmd, stdout=False, stdin=False)
        docker_client.exec_start(execid=id, detach=not wait)
        return self

    def copy_from_container(self, guest_path, host_path=None):
        data = docker_client.copy(self.container_name, guest_path)
        if host_path:
            with open(os.path.abspath(os.path.expanduser(host_path)), 'wb') as f:
                f.write(data)
        else:
            return data

    def stop(self):
        docker_client.stop(self.container_name)
        return self

    def commit(self, image_name):
        docker_client.commit(self.container_name, image_name)
        return self

    def remove_container(self):
        docker_client.remove_container(self.container_name)
        return self
