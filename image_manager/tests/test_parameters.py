# encoding: utf-8

import mock
import os
import unittest

import DIM


class TestParameters(unittest.TestCase):

    def test_parameters_empty(self):
        drp = DIM.DockerRunParameters()
        self.assertIsInstance(drp, dict)
        self.assertDictContainsSubset(drp, dict(ports=[], volumes=[]))
        self.assertDictEqual(drp.kwargs, {})
        self.assertNotIn('host_config', drp)
        drp.finalize()
        self.assertNotIn('host_config', drp)

    def test_parameters_add_volume(self):
        drp = DIM.DockerRunParameters()
        drp.add_volume('toto:titi')
        self.assertEqual(drp['volumes'], [u'titi'])
        self.assertDictEqual(drp.kwargs,
                             {u'binds':
                                  {os.path.abspath(os.path.expanduser(u'toto')):
                                       {u'bind': u'titi', u'mode': u'rw'}}
                             })
        drp.add_volume('host:guest:ro')
        self.assertEqual(drp['volumes'], [u'titi', u'guest'])
        self.assertDictEqual(drp.kwargs,
                             {u'binds': {
                                 os.path.abspath(os.path.expanduser(u'toto')):
                                       {u'bind': u'titi', u'mode': u'rw'},
                                 os.path.abspath(os.path.expanduser(u'host')):
                                       {u'bind': u'guest', u'mode': u'ro'}
                                  }})
        drp.finalize()
        self.assertIn('host_config', drp)

    def test_parameters_add_port(self):
        pass


if __name__ == '__main__':
    unittest.main()
