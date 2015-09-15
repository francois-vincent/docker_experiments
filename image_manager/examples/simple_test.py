# encoding: utf-8

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(__file__, '..', '..', '..')))

from image_manager import DIM


Dockerfile = """
FROM ubuntu:14.04

RUN mkdir -p /var/lib/docker
COPY {toto_conf} /var/lib/docker/toto.conf

# Do nothing
CMD ["/bin/cat"]
"""

toto_conf = """
[main]
  value=1
[second]
  value=2
"""


def simple_image():
    dim = DIM.DockerImageManager(
        ('Dockerfile', Dockerfile), ('toto_conf', toto_conf),
        image_name='navitia_image',
        hostname='test.docker',
        volumes=('toto:titi', 'host:guest:ro'),
        ports=(85, '84', '8003:83', '80-82')
    )
    with dim.get_dockerfile() as dockerfile:
        print(dockerfile.read())


if __name__ == '__main__':
    simple_image()
