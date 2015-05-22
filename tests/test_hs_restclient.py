""" Test hs_restclient functionality, with HydroShare REST end points mocked using httmock.

    Note: tests must be run from 'tests' directory as in:

        python test_hs_restclient.py
"""

import sys
sys.path.append('../')
import unittest
from datetime import date, datetime

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


class TestGetResourceList(unittest.TestCase):

    def setUp(self):
        self.resource_titles = ["Untitled resource 1", "Untitled resource 2",
                                "Create via REST API and Python client library",
                                "Create via REST API and Python client library 2",
                                "Create via REST API and Python client library 3"]
        self.resource_ids = ['c165b6f8ec64405da004bfb8890c35ae',
                             '1a63d6c24b9b4b42b9a97abfab94f9c6',
                             '5a6e5a992b1046ae820fd3e79ee36107',
                             'c817e936ac1147639787c0d4688d6319',
                             '408acb6b870d4297b8b036edcd9c3c58']

    @with_httmock(mocks.hydroshare.resourceList_get)
    def test_get_resource_list(self):
        hs = HydroShare()
        res_list = hs.getResourceList()

        for (i, r) in enumerate(res_list):
            self.assertEquals(r['resource_title'], self.resource_titles[i])
            self.assertEquals(r['resource_id'], self.resource_ids[i])

    @with_httmock(mocks.hydroshare.resourceListFilterCreator_get)
    def test_get_resource_list_filter_creator(self):
        hs = HydroShare()
        res_list = hs.getResourceList(creator='bmiles')
        for (i, r) in enumerate(res_list):
            self.assertEquals(r['creator'], 'bmiles')

    @with_httmock(mocks.hydroshare.resourceListFilterDate_get)
    def test_get_resource_list_filter_date(self):
        hs = HydroShare()
        from_date = date(2015, 5, 20)
        res_list = hs.getResourceList(from_date=from_date)
        for (i, r) in enumerate(res_list):
            self.assertTrue(datetime.strptime(r['date_created'], '%m-%d-%Y').date() >= from_date)

        to_date = date(2015, 5, 21) # up to and including 5/21/2015
        res_list = hs.getResourceList(to_date=to_date)
        for (i, r) in enumerate(res_list):
            self.assertTrue(datetime.strptime(r['date_created'], '%m-%d-%Y').date() < to_date)

        from_date = date(2015, 5, 19)
        to_date = date(2015, 5, 22) # up to and including 5/21/2015
        res_list = hs.getResourceList(from_date=from_date, to_date=to_date)
        for (i, r) in enumerate(res_list):
            self.assertTrue(datetime.strptime(r['date_created'], '%m-%d-%Y').date() >= from_date)
            self.assertTrue(datetime.strptime(r['date_created'], '%m-%d-%Y').date() < to_date)

    @with_httmock(mocks.hydroshare.resourceListFilterType_get)
    def test_get_resource_list_filter_type(self):
        hs = HydroShare()
        res_list = hs.getResourceList(types=('RasterResource',))
        for (i, r) in enumerate(res_list):
            self.assertEquals(r['resource_type'], 'RasterResource')

if __name__ == '__main__':
    unittest.main()
