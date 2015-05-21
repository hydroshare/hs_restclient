""" Test hs_restclient functionality, with HydroShare REST end points mocked using httmock.

    Note: tests must be run from 'tests' directory as in:

        python test_hs_restclient.py
"""

import sys
sys.path.append('../')
import unittest

from httmock import with_httmock

from hs_restclient import HydroShare
import mocks.hydroshare


class TestGetResourceTypes(unittest.TestCase):

    def setUp(self):
        pass

    @with_httmock(mocks.hydroshare.resourceTypes_get)
    def test_get_resource_types(self):
        hs = HydroShare()
        res_type_proto = {u'GenericResource',
                          u'ModelInstanceResource',
                          u'ModelProgramResource',
                          u'NetcdfResource',
                          u'RasterResource',
                          u'RefTimeSeries',
                          u'SWATModelInstanceResource',
                          u'TimeSeriesResource',
                          u'ToolResource'}

        res_types = hs.getResourceTypes()
        self.assertSetEqual(res_type_proto, res_types)


if __name__ == '__main__':
    unittest.main()
