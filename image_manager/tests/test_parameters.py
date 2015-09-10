# encoding: utf-8

import mock
import os
import unittest
import sys
sys.path.insert(1, os.path.abspath(os.path.join(__file__, '..', '..')))

import DIM
DIM.log = mock


class TestParameters(unittest.TestCase):

    def test_parameters_empty(self):
        drp = DIM.DockerRunParameters()
        assert isinstance(drp, dict)
        self.assertDictContainsSubset(drp, dict(ports=[], volumes=[]))
        assert hasattr(drp, 'kwargs')
        assert drp.kwargs == {}
        assert 'host_config' not in drp
        drp.finalize()
        assert 'host_config' not in drp

    def test_parameters_add_volume(self):
        drp = DIM.DockerRunParameters()
        drp.add_volume('toto:titi')
        assert drp['volumes'] == [u'titi']
        assert drp.kwargs == {u'binds': {
            os.path.abspath(os.path.expanduser(u'toto')): {u'bind': u'titi', u'mode': u'rw'}
        }}
        drp.add_volume('host:guest:ro')
        assert drp['volumes'] == [u'titi', u'guest']
        assert drp.kwargs == {u'binds': {
            os.path.abspath(os.path.expanduser(u'toto')): {u'bind': u'titi', u'mode': u'rw'},
            os.path.abspath(os.path.expanduser(u'host')): {u'bind': u'guest', u'mode': u'ro'}
        }}
        drp.finalize()
        assert 'host_config' in drp

    def test_parameters_add_port(self):
        drp = DIM.DockerRunParameters()
        drp.add_port(85)
        assert drp['ports'] == [85]
        assert drp.kwargs == {u'port_bindings': {
            85: None
        }}
        drp.add_port('84')
        assert drp['ports'] == [84, 85]
        drp.add_port('8003:83')
        assert drp['ports'] == [83, 84, 85]
        assert drp.kwargs == {u'port_bindings': {
            85: None,
            84: None,
            83: 8003
        }}
        drp.add_port('80-82')
        # ports are sorted
        assert drp['ports'] == [80, 81, 82, 83, 84, 85]
        assert drp.kwargs == {u'port_bindings': {
            85: None,
            84: None,
            83: 8003,
            82: None,
            81: None,
            80: None,
        }}
        drp.finalize()
        assert 'host_config' in drp


if __name__ == '__main__':
    unittest.main()
