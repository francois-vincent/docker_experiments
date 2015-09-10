# encoding: utf-8

from __future__ import unicode_literals, print_function
from io import BytesIO
import os
import random

import docker

docker_client = docker.Client(base_url='unix://var/run/docker.sock', version='auto')


# Helper functions and classes
# ============================

def wait(iterable):
    for line in iterable:
        log.debug(line)
        if line.startswith(b'{"errorDetail'):
            raise RuntimeError("Build failed @" + line)


def random_hex(len=32):
    return ''.join(random.choice('0123456789abcdef') for _ in xrange(len))


def render(string, context):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return string.format(context)


# Main classes
# ============

class DockerRunParameters(dict):
    """
    A class to define parameters for the docker create/run commands.
    """

    def __init__(self, **options):
        dict.__init__(self)
        self.kwargs = {}
        self['volumes'] = []
        self['ports'] = []
        volumes = options.pop('volumes', None)
        ports = options.pop('ports', None)
        if volumes:
            for vol in volumes:
                self.add_volume(vol)
        if ports:
            for port in ports:
                self.add_port(port)
        self.update(options)
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
        self['volumes'].append(guest)
        binds[host] = {'bind': guest, 'mode': mode}

    def add_port(self, port):
        port_bindings = self.kwargs.setdefault('port_bindings', {})
        if isinstance(port, basestring):
            if ':' in port:
                # TODO does not accept format host_ip:host_port:guest_port yet
                host, guest = port.rsplit(':', 1)
                guest = int(guest)
                port_bindings[guest] = int(host)
                self['ports'].append(guest)
            elif '-' in port:
                start, end = port.split('-')
                for p in xrange(int(start), int(end) + 1):
                    port_bindings[p] = None
                    self['ports'].append(p)
            else:
                port = int(port)
                port_bindings[port] = None
                self['ports'].append(port)
        else:
            port_bindings[port] = None
            self['ports'].append(port)
        self['ports'].sort()

    def finalize(self):
        if self.kwargs:
            self['host_config'] = docker.utils.create_host_config(**self.kwargs)


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

    # Helper methods
    # --------------

    def get_container_name(self):
        if not getattr(self, 'container_name'):
            self.container_name = self.image_name[:12] + '_' + random_hex(10)
        return self.container_name

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

    # Image methods
    # -------------

    def image_build(self):
        self.log.info("Building image {}".format(self.image_name))
        wait(docker_client.build(fileobj=self.get_dockerfile(), tag=self.image_name, rm=True))
        return self

    def image_destroy(self, image_name=None):
        image_name = image_name or self.image_name
        print("Removing image '{}'".format(image_name))
        try:
            docker_client.remove_image(image=image_name)
        except docker.errors.APIError:
            print("  image not found")
        return self

    # Container methods
    # -----------------

    def container_create(self, parameters, start=True):
        kwargs = dict(image=self.image_name, name=self.container_name, hostname=self.host)
        if self.volumes or self.ports:
            kwargs['host_config'] = self.host_config
            if self.ports:
                kwargs['ports'] = self.ports
            if self.volumes:
                kwargs['volumes'] = self.volumes
        try:
            self.container = docker_client.create_container(**kwargs).get('Id')
        except docker.errors.APIError:
            docker_client.pull(self.image_name)
            self.container = docker_client.create_container(**kwargs).get('Id')
        return self

    def container_start(self):
        return self

    def container_inspect(self, field='NetworkSettings.IPAddress'):
        config = docker_client.inspect_container(container=self.get_container_name())
        if field:
            for x in field.split('.'):
                if x:
                    config = config.get(x)
        return config

    def container_exec(self):
        return self

    def container_copy(self):
        return self

    def container_stop(self):
        return self

    def commit(self, image_name):
        docker_client.commit(self.get_container_name(), image_name)
        return self

    def container_remove(self):
        return self
