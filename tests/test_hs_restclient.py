""" Test hs_restclient functionality, with HydroShare REST end points mocked using httmock.

    Note: tests must be run from 'tests' directory as in:

        python test_hs_restclient.py
"""
import os
import sys
sys.path.append('../')
import unittest
from datetime import date, datetime
import tempfile
import shutil
from zipfile import ZipFile
import difflib
import filecmp

from httmock import with_httmock, HTTMock

from hs_restclient import HydroShare
import mocks.hydroshare

try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring

class TestGetResourceTypes(unittest.TestCase):

    def setUp(self):
        pass

    @with_httmock(mocks.hydroshare.resourceTypes_get)
    def test_get_resource_types(self):
        hs = HydroShare()
        res_type_proto = {'GenericResource',
                          'ModelInstanceResource',
                          'ModelProgramResource',
                          'NetcdfResource',
                          'RasterResource',
                          'RefTimeSeries',
                          'SWATModelInstanceResource',
                          'TimeSeriesResource',
                          'ToolResource'}

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

    @with_httmock(mocks.hydroshare.resourceList_get)
    def test_get_resource_list_lenght(self):
        hs = HydroShare()
        res_list = hs.getResourceList()
        self.assertEquals(res_list.lenght(), 4)

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

    def test_create_get_delete_resource(self):
        hs = HydroShare()

        abstract = 'Abstract for hello world resource'
        title = 'Minimal hello world resource'
        keywords = ('hello', 'world')
        rtype = 'GenericResource'
        fname = 'mocks/data/minimal_resource_file.txt'

        with HTTMock(mocks.hydroshare.createResourceCRUD):
            # Create
            newres = hs.createResource(rtype, title, resource_file=fname, keywords=keywords, abstract=abstract)
            self.assertIsNotNone(newres)
            sysmeta = hs.getSystemMetadata(newres)
            self.assertEqual(sysmeta['resource_id'], newres)
            self.assertEqual(sysmeta['resource_type'], rtype)
            self.assertFalse(sysmeta['public'])

        with HTTMock(mocks.hydroshare.accessRules_put):
            # Make resource public
            hs.setAccessRules(newres, public=True)
            sysmeta = hs.getSystemMetadata(newres)
            self.assertTrue(sysmeta['public'])

        with HTTMock(mocks.hydroshare.createResourceCRUD):
            # Get
            tmpdir = tempfile.mkdtemp()
            hs.getResource(newres, destination=tmpdir)
            with ZipFile(os.path.join(tmpdir, '0b047b77767e46c6b6f525a2f386b9fe.zip'), 'r') as zfile:
                contents = zfile.namelist()
                self.assertEqual(contents[0], '2015.05.22.13.14.24/')
                downloaded = zfile.open('2015.05.22.13.14.24/data/contents/minimal_resource_file.txt', 'r')
                original = open('mocks/data/minimal_resource_file.txt', 'r')
                self.assertEqual(downloaded.read(), original.read())
                downloaded.close()
                original.close()
            shutil.rmtree(tmpdir)

            # Delete
            delres = hs.deleteResource(newres)
            self.assertEqual(delres, newres)

    @with_httmock(mocks.hydroshare.resourceFileCRUD)
    def test_create_get_delete_resource_file(self):
        hs = HydroShare()
        # Add
        res_id = '0b047b77767e46c6b6f525a2f386b9fe'
        fpath = 'mocks/data/another_resource_file.txt'
        fname = os.path.basename(fpath)
        resp = hs.addResourceFile(res_id, fpath)
        self.assertEqual(resp, res_id)

        # Get
        tmpdir = tempfile.mkdtemp()
        res_file = hs.getResourceFile(res_id, fname, destination=tmpdir)
        self.assertTrue(filecmp.cmp(res_file, fpath, shallow=False))
        shutil.rmtree(tmpdir)

        # Delete
        delres = hs.deleteResourceFile(res_id, fname)
        self.assertEqual(delres, res_id)


if __name__ == '__main__':
    unittest.main()
