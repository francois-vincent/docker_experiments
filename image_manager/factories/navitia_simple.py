# encoding: utf-8


def absjoin(*p):
    return os.path.abspath(os.path.join(*p))

import os.path
ROOT = absjoin(__file__, '..', '..', '..')
import sys
sys.path[0] = ROOT

from clingon import clingon
clingon.DEBUG = True

from image_manager import DIM

IMAGE_NAME = 'navitia_simple'


@clingon.clize
def factory(host_data_folder, source='debian8'):
    drp = DIM.DockerRunParameters(
        hostname=IMAGE_NAME,
        volumes=(host_data_folder + ':/srv/ed/data',),
        ports=('8080:80',)
    )
    df = DIM.DockerFile(
        os.path.join(source, 'Dockerfile'),
        parameters=drp,
        add_ons=('apache', 'user', 'french', 'postgres', 'sshserver', 'rabbitmq', 'redis', 'supervisor'),
        template_context=dict(user='navitia', password='navitia', home_ssh='/home/navitia/.ssh',
                              unsecure_key_pub=os.path.join(ROOT, 'ssh', 'unsecure_key.pub'),
                              supervisord_conf=absjoin(__file__, '..', IMAGE_NAME, 'supervisord.conf')
        )
    )
    dim = DIM.DockerImageManager(df, image_name=IMAGE_NAME)
