"""
Test hs_restclient functionality, with HydroShare REST end points mocked
using httmock.

    Note: tests must be run from 'tests' directory as in:

        python test_hs_restclient.py
"""
import os
import sys
import unittest
from datetime import date, datetime
import tempfile
import shutil
from zipfile import ZipFile
import filecmp
import json

from httmock import with_httmock, HTTMock

from hs_restclient import HydroShare
import mocks.hydroshare


sys.path.append('../')


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
            self.assertEqual(r['resource_title'], self.resource_titles[i])
            self.assertEqual(r['resource_id'], self.resource_ids[i])

    @with_httmock(mocks.hydroshare.resourceListFilterCreator_get)
    def test_get_resource_list_filter_creator(self):
        hs = HydroShare()
        res_list = hs.getResourceList(creator='bmiles')
        for (i, r) in enumerate(res_list):
            self.assertEqual(r['creator'], 'bmiles')

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
        # time.sleep(1)
        for (i, r) in enumerate(res_list):
            self.assertTrue(datetime.strptime(r['date_created'], '%m-%d-%Y').date() >= from_date)
            self.assertTrue(datetime.strptime(r['date_created'], '%m-%d-%Y').date() < to_date)

    @with_httmock(mocks.hydroshare.resourceListFilterType_get)
    def test_get_resource_list_filter_type(self):
        hs = HydroShare()
        res_list = hs.getResourceList(types=('RasterResource',))
        for (i, r) in enumerate(res_list):
            self.assertEqual(r['resource_type'], 'RasterResource')

    def test_create_get_delete_resource(self):
        hs = HydroShare()

        abstract = 'Abstract for hello world resource'
        title = 'Minimal hello world resource'
        keywords = ('hello', 'world')
        rtype = 'GenericResource'
        fname = 'mocks/data/minimal_resource_file.txt'
        metadata = json.dumps([{'coverage': {'type': 'period', 'start': '01/01/2000',
                                             'end': '12/12/2010'}}])

        with HTTMock(mocks.hydroshare.createResourceCRUD):
            # Create
            newres = hs.createResource(rtype, title, resource_file=fname, keywords=keywords,
                                       abstract=abstract, metadata=metadata)
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
            with ZipFile(os.path.join(tmpdir, '511debf8858a4ea081f78d66870da76c.zip'), 'r') as zfile:
                self.assertTrue('511debf8858a4ea081f78d66870da76c/data/contents/minimal_resource_file.txt' in zfile.namelist())
                downloaded = zfile.open('511debf8858a4ea081f78d66870da76c/data/contents/minimal_resource_file.txt', 'r')
                original = open('mocks/data/minimal_resource_file.txt', 'rb')
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
        res_id = '511debf8858a4ea081f78d66870da76c'
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


class TestGetUserInfo(unittest.TestCase):

    @with_httmock(mocks.hydroshare.userInfo_get)
    def test_get_user_info(self):
        hs = HydroShare()
        user_info = hs.getUserInfo()

        self.assertEqual(user_info['username'], 'username')
        self.assertEqual(user_info['first_name'], 'First')
        self.assertEqual(user_info['last_name'], 'Last')
        self.assertEqual(user_info['email'], 'user@domain.com')


class TestGetScimeta(unittest.TestCase):

    @with_httmock(mocks.hydroshare.scimeta_get)
    def test_get_scimeta(self):
        hs = HydroShare()
        scimeta = hs.getScienceMetadata('6dbb0dfb8f3a498881e4de428cb1587c')
        self.assertTrue(scimeta.find("""<rdf:Description rdf:about="http://www.hydroshare.org/resource/6dbb0dfb8f3a498881e4de428cb1587c">""") != -1)


class TestGetResourceFileList(unittest.TestCase):

    def setUp(self):
        self.urls = [
            "http://www.hydroshare.org/django_irods/download/511debf8858a4ea081f78d66870da76c/data/contents/foo/bar.txt",
            "http://www.hydroshare.org/django_irods/download/511debf8858a4ea081f78d66870da76c/data/contents/dem.tif",
            "http://www.hydroshare.org/django_irods/download/511debf8858a4ea081f78d66870da76c/data/contents/data.csv",
            "http://www.hydroshare.org/django_irods/download/511debf8858a4ea081f78d66870da76c/data/contents/data.sqlite",
            "http://www.hydroshare.org/django_irods/download/511debf8858a4ea081f78d66870da76c/data/contents/viz.png"
        ]
        self.sizes = [
            23550,
            107545,
            148,
            267118,
            128
        ]
        self.content_types = [
            "text/plain",
            "image/tiff",
            "text/csv",
            "application/x-sqlite3",
            "image/png"
        ]

    @with_httmock(mocks.hydroshare.resourceFileList_get)
    def test_get_resource_file_list(self):
        hs = HydroShare()
        res_list = hs.getResourceFileList('511debf8858a4ea081f78d66870da76c')

        for (i, r) in enumerate(res_list):
            self.assertEqual(r['url'], self.urls[i])
            self.assertEqual(r['size'], self.sizes[i])
            self.assertEqual(r['content_type'], self.content_types[i])


if __name__ == '__main__':
    unittest.main()
