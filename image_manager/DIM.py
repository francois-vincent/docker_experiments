# encoding: utf-8

"""
DIM: Docker Image Manager
A set of convenience classes to create and manage Docker Images and Containers
"""

# TODO warning path out of build context !

from __future__ import unicode_literals, print_function
from contextlib import contextmanager
from io import BytesIO
import os
ROOT = os.path.abspath(os.path.dirname(__file__))

import docker

from utils import wait, random_hex, render, chain_temp_files

docker_client = docker.Client(base_url='unix://var/run/docker.sock', version='auto')


class DockerRunParameters(dict):
    """
    A class to define parameters for the docker create/run commands.
    Is also used to enrich Dockerfile EXPOSE and VOLUME instructions.
    """
    allowed = ()

    def __init__(self, **options):
        dict.__init__(self)
        self.log = options.pop('log', log)
        volumes = options.pop('volumes', ())
        ports = options.pop('ports', ())
        self.update(options)
        self.kwargs = {}
        for vol in volumes:
            self.add_volume(vol)
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
        # TODO provide true, chainable composition
        res = dict(self)
        res.update(other)
        return res


class DockerFile(object):
    """
    A class to manage Dockerfile like objects
    """
    def __init__(self, *files, **options):
        self.log = options.pop('log', log)
        # this is the global context used by every template involved in the build process
        # templates can be Dockerfile, configuration files, ...
        self.template_context = options.pop('template_context', None) or {}
        # a file can be a real file, specified by a path,
        # or a pseudo file, specified via a (name, content) pair
        self.files = {}
        for file in files:
            if isinstance(file, tuple):
                name, content = file
            else:
                name = os.path.basename(file)
                with open(os.path.expanduser(file), 'rb') as f:
                    content = f.read()
            if name.lower() == 'dockerfile':
                self.dockerfile = content
            else:
                self.files[name] = content
        self.__dict__.update(options)
        if not hasattr(self, 'dockerfile'):
            raise ValueError("No Dockerfile specified")

    def process_parameters(self):
        if 'ports' in self.parameters and not '\nEXPOSE' in self.dockerfile:
            ports = list(self.parameters['ports'])
            ports.sort()
            extension = '\nEXPOSE ' + ' '.join(str(p) for p in ports) + '\n'
            self.dockerfile += extension
        if 'volumes' in self.parameters and not '\nVOLUME' in self.dockerfile:
            extension = '\nVOLUME ["' + '" "'.join(str(p) for p in self.parameters['volumes']) + '"]\n'
            self.dockerfile += extension
        return self

    def process_addons(self):
        if hasattr(self, 'add_ons'):
            for add_on in self.add_ons:
                with open(os.path.join(ROOT, 'addons', add_on)) as f:
                    self.dockerfile += f.read()
        return self

    @contextmanager
    def get_dockerfile(self, process=True):
        """ Docker file is specified either via a string or a file.
            Then it is rendered according to an optional context (dictionary).
        """
        if process:
            self.process_addons().process_parameters()
        with chain_temp_files(self.files, self.template_context):
            yield BytesIO(render(self.dockerfile, self.template_context))


class DockerImageManager(object):
    """
    A class to manage Docker images, wich features:
    - Creating a new image out of an existing image.
    - Creating a new image out of a Dockerfile that can be inline or file,
      raw or template.
    - Running an image with a set of parameters.
    - Pushing an image to dockerhub, provided the user is logged in.
    An instance manages a single image.
    """

    def __init__(self, source, **kwargs):
        self.source = source
        kwargs['image'] = self.image_name = kwargs.pop('image_name', None) or self.random_name()
        self.log = kwargs.pop('log', log)
        self.log.debug("New {}(image_name='{}')".format(self.__class__.__name__, self.image_name))
        self.parameters = kwargs.pop('parameters', None) or DockerRunParameters(**kwargs)

    @staticmethod
    def random_name():
        return random_hex()

    def pull(self):
        docker_client.pull(self.source)
        return self

    def build(self):
        self.log.info("Building image {}".format(self.image_name))
        with self.source.get_dockerfile() as dockerfile:
            wait(docker_client.build(fileobj=dockerfile, tag=self.image_name, rm=True))
        return self

    def resolve_tag(self, image_name, tag):
        image_name = image_name or self.image_name
        try:
            image_name, _tag = image_name.split(':')
            tag = tag or _tag
        except ValueError:
            pass
        return image_name, tag

    def push(self, image_name=None, tag=None):
        image_name, tag = self.resolve_tag(image_name, tag)
        if tag:
            self.log.info("Pushing image '{}:{}'".format(image_name, tag))
            docker_client.push(image_name, tag)
        else:
            self.log.info("Pushing image '{}'".format(image_name))
            docker_client.push(image_name)
        return self

    def inspect(self):
        return docker_client.inspect_image(image_id=self.image_name)

    def remove_image(self, image_name=None, tag=None):
        image_name, tag = self.resolve_tag(image_name, tag)
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
        kwargs['name'] = self.container_name = kwargs.pop('container_name', None) or self.random_name()
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
