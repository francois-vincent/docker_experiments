# encoding: utf-8

import mock
import os

try:
    import unittest
except ImportError:
    class unittest(object):
        TestCase = object
        @staticmethod
        def main():
            print("Please install unittest, or run with py.test")
import sys
sys.path.insert(1, os.path.abspath(os.path.join(__file__, '..', '..')))

import DIM
DIM.log = mock.Mock()
DIM.docker_client = mock.Mock()


class TestParameters(unittest.TestCase):

    def test_parameters_empty(self):
        drp = DIM.DockerRunParameters()
        assert isinstance(drp, dict)
        assert drp == {}
        assert hasattr(drp, 'kwargs')
        assert drp.kwargs == {}
        assert 'host_config' not in drp
        drp.finalize()
        assert 'host_config' not in drp

    def test_parameters_add_volume(self):
        drp = DIM.DockerRunParameters()
        drp.add_volume('toto:titi')
        assert drp['volumes'] == set((u'titi',))
        assert drp.kwargs == {u'binds': {
            os.path.abspath(os.path.expanduser(u'toto')): {u'bind': u'titi', u'mode': u'rw'}
        }}
        drp.add_volume('host:guest:ro')
        assert drp['volumes'] == set((u'titi', u'guest'))
        assert drp.kwargs == {u'binds': {
            os.path.abspath(os.path.expanduser(u'toto')): {u'bind': u'titi', u'mode': u'rw'},
            os.path.abspath(os.path.expanduser(u'host')): {u'bind': u'guest', u'mode': u'ro'}
        }}
        drp.finalize()
        assert 'host_config' in drp

    def test_parameters_add_port(self):
        drp = DIM.DockerRunParameters()
        drp.add_port(85)
        assert drp['ports'] == set((85,))
        assert drp.kwargs == {u'port_bindings': {
            85: None
        }}
        drp.add_port('84')
        assert drp['ports'] == set((84, 85))
        drp.add_port('8003:83')
        assert drp['ports'] == set((83, 84, 85))
        assert drp.kwargs == {u'port_bindings': {
            85: None, 84: None, 83: 8003
        }}
        drp.add_port('80-82')
        assert drp['ports'] == set((80, 81, 82, 83, 84, 85))
        assert drp.kwargs == {u'port_bindings': {
            85: None, 84: None, 83: 8003, 82: None, 81: None, 80: None
        }}
        drp.finalize()
        assert 'host_config' in drp

    def test_parameters_init(self):
        drp = DIM.DockerRunParameters(
            image_name='navitia_image',
            hostname='test.docker',
            volumes=('toto:titi', 'host:guest:ro'),
            ports=(85, '84', '8003:83', '80-82')
        )
        drp.finalize()
        assert 'host_config' in drp
        assert drp['volumes'] == set((u'titi', u'guest'))
        assert drp['ports'] == set((80, 81, 82, 83, 84, 85))
        assert drp['image_name'] == 'navitia_image'
        assert drp['hostname'] == 'test.docker'
        assert drp.kwargs == {
            u'binds': {
                os.path.abspath(os.path.expanduser(u'toto')): {u'bind': u'titi', u'mode': u'rw'},
                os.path.abspath(os.path.expanduser(u'host')): {u'bind': u'guest', u'mode': u'ro'}
            },
            u'port_bindings': {
                85: None, 84: None, 83: 8003, 82: None, 81: None, 80: None
            }
        }


class TestDockerImage(unittest.TestCase):

    def test_simple_image(self):
        dim = DIM.DockerImageManager(image_name='navitia')
        assert dim.image_name == 'navitia'
        assert dim.parameters == {'image': 'navitia'}
        assert dim.log == DIM.log
        assert dim.dockerfile_string == None
        assert dim.dockerfile_name == None
        DIM.log.debug.assert_called_with(u"New DockerImageManager(image_name='navitia')")


class TestDockerContainer(unittest.TestCase):

    def test_simple_container(self):
        dcm = DIM.DockerImageManager(image_name='navitia').get_container('simple')
        assert dcm.container_name == 'simple'
        assert dcm.parameters == {'image': 'navitia', 'name': 'simple'}
        assert dcm.log == DIM.log
        DIM.log.debug.assert_called_with(u"New DockerContainerManager(container_name='simple')")


if __name__ == '__main__':
    unittest.main()
