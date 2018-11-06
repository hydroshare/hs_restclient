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

import mocks.hydroshare

sys.path.append('../')
from hs_restclient import HydroShare, HydroShareAuthBasic


class TestGetResourceTypes(unittest.TestCase):

    def setUp(self):
        pass

    @with_httmock(mocks.hydroshare.resourceTypes_get)
    def test_get_resource_types(self):
        hs = HydroShare(prompt_auth=False)
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
        hs = HydroShare(prompt_auth=False)
        res_list = hs.getResourceList()

        for (i, r) in enumerate(res_list):
            self.assertEqual(r['resource_title'], self.resource_titles[i])
            self.assertEqual(r['resource_id'], self.resource_ids[i])

    @with_httmock(mocks.hydroshare.resourceListFilterCreator_get)
    def test_get_resource_list_filter_creator(self):
        hs = HydroShare(prompt_auth=False)
        res_list = hs.getResourceList(creator='bmiles')
        for (i, r) in enumerate(res_list):
            self.assertEqual(r['creator'], 'bmiles')

    @with_httmock(mocks.hydroshare.resourceListFilterDate_get)
    def test_get_resource_list_filter_date(self):
        hs = HydroShare(prompt_auth=False)
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
        hs = HydroShare(prompt_auth=False)
        res_list = hs.getResourceList(types=('RasterResource',))
        for (i, r) in enumerate(res_list):
            self.assertEqual(r['resource_type'], 'RasterResource')

    def test_create_get_delete_resource(self):
        hs = HydroShare(prompt_auth=False)

        abstract = 'Abstract for hello world resource'
        title = 'Minimal hello world resource'
        keywords = ('hello', 'world')
        rtype = 'GenericResource'
        fname = 'mocks/data/minimal_resource_file.txt'
        metadata = json.dumps([{'coverage': {'type': 'period', 'value': {'start': '01/01/2000',
                                             'end': '12/12/2010'}}},
                               {'creator': {'name': 'John Smith'}},
                               {'contributor': {'name': 'Lisa Miller'}}])

        extra_metadata = json.dumps({'latitude': '40', 'longitude': '-111'})

        with HTTMock(mocks.hydroshare.createResourceCRUD):
            # Create
            newres = hs.createResource(rtype, title, resource_file=fname, keywords=keywords,
                                       abstract=abstract, metadata=metadata, extra_metadata=extra_metadata)
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
        hs = HydroShare(prompt_auth=False)
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
        hs = HydroShare(prompt_auth=False)
        user_info = hs.getUserInfo()

        self.assertEqual(user_info['username'], 'username')
        self.assertEqual(user_info['first_name'], 'First')
        self.assertEqual(user_info['last_name'], 'Last')
        self.assertEqual(user_info['email'], 'user@domain.com')


class TestScimeta(unittest.TestCase):

    @with_httmock(mocks.hydroshare.scimeta_xml_get)
    def test_get_scimeta_xml(self):
        hs = HydroShare(prompt_auth=False)
        scimeta = hs.getScienceMetadataRDF('6dbb0dfb8f3a498881e4de428cb1587c')
        self.assertTrue(scimeta.find("""<rdf:Description rdf:about="http://www.hydroshare.org/resource/6dbb0dfb8f3a498881e4de428cb1587c">""") != -1)

    @with_httmock(mocks.hydroshare.scimeta_json_get)
    def test_get_scimeta_json(self):
        hs = HydroShare(prompt_auth=False)
        scimeta = hs.getScienceMetadata('511debf8858a4ea081f78d66870da76c')

        self.assertEqual(scimeta['title'], 'Great Salt Lake Level and Volume')
        self.assertEqual(len(scimeta['creators']), 2)
        self.assertEqual(len(scimeta['contributors']), 1)
        self.assertEqual(len(scimeta['coverages']), 1)
        self.assertEqual(len(scimeta['dates']), 2)
        self.assertEqual(scimeta['description'], 'Time series of level, area and volume in the Great Salt Lake. Volume and area of the Great Salt Lake are derived from recorded levels')
        self.assertEqual(scimeta['formats'][0]['value'], 'image/tiff')
        self.assertEqual(len(scimeta['funding_agencies']), 1)
        self.assertEqual(len(scimeta['identifiers']), 1)
        self.assertEqual(scimeta['language'], 'eng')
        self.assertEqual(scimeta['rights'], 'This resource is shared under the Creative Commons Attribution CC BY. http://creativecommons.org/licenses/by/4.0/')
        self.assertEqual(scimeta['type'], 'http://www.hydroshare.org/terms/GenericResource')
        self.assertEqual(scimeta['publisher'], None)
        self.assertEqual(len(scimeta['sources']), 0)
        self.assertEqual(len(scimeta['relations']), 0)
        self.assertEqual(len(scimeta['subjects']), 2)

    @with_httmock(mocks.hydroshare.scimeta_json_put)
    def test_update_scimeta(self):
        hs = HydroShare(prompt_auth=False)
        metadata_to_update = {'title': 'Updated resource title'}
        scimeta = hs.updateScienceMetadata('511debf8858a4ea081f78d66870da76c', metadata=metadata_to_update)

        self.assertEqual(scimeta['title'], 'Updated resource title')
        self.assertEqual(len(scimeta['creators']), 2)
        self.assertEqual(len(scimeta['contributors']), 1)
        self.assertEqual(len(scimeta['coverages']), 1)
        self.assertEqual(len(scimeta['dates']), 2)
        self.assertEqual(scimeta['description'],
                         'Time series of level, area and volume in the Great Salt Lake. Volume and area of the Great Salt Lake are derived from recorded levels')
        self.assertEqual(scimeta['formats'][0]['value'], 'image/tiff')
        self.assertEqual(len(scimeta['funding_agencies']), 1)
        self.assertEqual(len(scimeta['identifiers']), 1)
        self.assertEqual(scimeta['language'], 'eng')
        self.assertEqual(scimeta['rights'],
                         'This resource is shared under the Creative Commons Attribution CC BY. http://creativecommons.org/licenses/by/4.0/')
        self.assertEqual(scimeta['type'], 'http://www.hydroshare.org/terms/GenericResource')
        self.assertEqual(scimeta['publisher'], None)
        self.assertEqual(len(scimeta['sources']), 0)
        self.assertEqual(len(scimeta['relations']), 0)
        self.assertEqual(len(scimeta['subjects']), 2)


class TestGetResourceMap(unittest.TestCase):

    @with_httmock(mocks.hydroshare.resourcemap_get)
    def test_get_resourcemap(self):
        hs = HydroShare(prompt_auth=False)
        resourcemap = hs.getResourceMap('6dbb0dfb8f3a498881e4de428cb1587c')
        self.assertTrue(resourcemap.find("""<rdf:Description rdf:about="http://www.hydroshare.org/resource/6dbb0dfb8f3a498881e4de428cb1587c">""") != -1)


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
        hs = HydroShare(prompt_auth=False)
        res_list = hs.getResourceFileList('511debf8858a4ea081f78d66870da76c')

        for (i, r) in enumerate(res_list):
            self.assertEqual(r['url'], self.urls[i])
            self.assertEqual(r['size'], self.sizes[i])
            self.assertEqual(r['content_type'], self.content_types[i])


class TestResourceFolderCRUD(unittest.TestCase):

    @with_httmock(mocks.hydroshare.resourceFolderContents_get)
    def test_get_folder_contents(self):
        hs = HydroShare(prompt_auth=False)
        folder_contents = hs.getResourceFolderContents('511debf8858a4ea081f78d66870da76c', pathname='model/initial/')

        self.assertEqual(folder_contents['resource_id'], '511debf8858a4ea081f78d66870da76c')
        self.assertEqual(folder_contents['path'], 'model/initial')
        self.assertEqual(folder_contents['files'], ["model.exe", "param.txt"])
        self.assertEqual(folder_contents['folders'], ["run/1", "run/2"])

    @with_httmock(mocks.hydroshare.resourceFolderCreate_put)
    def test_folder_create(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.createResourceFolder('511debf8858a4ea081f78d66870da76c', pathname='model/initial/')

        self.assertEqual(response['resource_id'], '511debf8858a4ea081f78d66870da76c')
        self.assertEqual(response['path'], 'model/initial')

    @with_httmock(mocks.hydroshare.resourceFolderDelete_delete)
    def test_folder_delete(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.deleteResourceFolder('511debf8858a4ea081f78d66870da76c', pathname='model/initial/')

        self.assertEqual(response['resource_id'], '511debf8858a4ea081f78d66870da76c')
        self.assertEqual(response['path'], 'model/initial')


class TestResourceCopy(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceCopy_post)
    def test_resource_copy(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').copy()
        self.assertNotEqual('6dbb0dfb8f3a498881e4de428cb1587c', response)
        self.assertEqual(response.status_code, 202)


class TestResourceVersion(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceVersion_post)
    def test_resource_copy(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').version()
        self.assertNotEqual('6dbb0dfb8f3a498881e4de428cb1587c', response)
        self.assertEqual(response.status_code, 202)


class TestResourceSetFileType(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceSetFileType_post)
    def test_set_file_type(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').functions.set_file_type(
            {"file_path": "file_path",
             "hs_file_type": "NetCDF"})
        self.assertEqual(response.status_code, 202)


class TestResourceFlags(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceFlags_post)
    def test_resource_flag_make_public(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').flag({
            "t": "make_public"
        })
        self.assertEqual(response.status_code, 202)

    @with_httmock(mocks.hydroshare.resourceFlags_post)
    def test_resource_flag_make_public(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').flag({
            "t": "make_private"
        })
        self.assertEqual(response.status_code, 202)

    @with_httmock(mocks.hydroshare.resourceFlags_post)
    def test_resource_flag_make_discoverable(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').flag({
            "t": "make_discoverable"
        })
        self.assertEqual(response.status_code, 202)

    @with_httmock(mocks.hydroshare.resourceFlags_post)
    def test_resource_flag_make_not_discoverable(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').flag({
            "t": "make_not_discoverable"
        })
        self.assertEqual(response.status_code, 202)

    @with_httmock(mocks.hydroshare.resourceFlags_post)
    def test_resource_flag_make_shareable(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').flag({
            "t": "make_shareable"
        })
        self.assertEqual(response.status_code, 202)

    @with_httmock(mocks.hydroshare.resourceFlags_post)
    def test_resource_flag_make_not_shareable(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').flag({
            "t": "make_not_shareable"
        })
        self.assertEqual(response.status_code, 202)


class TestResourceScimetaCustom(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceScimetaCustom_post)
    def test_resource_scimeta_custom(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').scimeta.custom({
            "foo": "bar",
            "foo2": "bar2"
        })
        self.assertEqual(response.status_code, 200)


class TestResourceMoveFileOrFolder(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceMoveFileOrFolder_post)
    def test_resource_move_or_rename(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').functions.move_or_rename({
            "source_path": "/source/path",
            "target_path": "/target/path"
        })
        self.assertEqual(response.status_code, 200)


class TestResourceZipUnzip(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceZipFolder_post)
    def test_resource_zip_folder(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').functions.zip({
            "input_coll_path": "/source/path",
            "output_zip_fname": "filename.zip",
            "remove_original_after_zip": True
        })
        self.assertEqual(response.status_code, 200)
    '''
    @with_httmock(mocks.hydroshare.resourceUnzipFile_post)
    def test_resource_unzip_file(self):
        hs = HydroShare(prompt_auth=False)
        response = hs.resource('511debf8858a4ea081f78d66870da76c').functions.unzip({
            "zip_with_rel_path": "/path/to/zip",
            "remove_original_zip": True
        })
        self.assertEqual(response.status_code, 200)
    '''
'''
class TestResourceUploadFileToFolder(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceUploadFile_post)
    def test_resource_upload_file(self):
        hs = HydroShare(prompt_auth=False)

        response = hs.resource('511debf8858a4ea081f78d66870da76c').files({
            "file": 'mocks/data/another_resource_file.txt',
            "folder": "/target/folder"
        })
        self.assertEqual(response.status_code, 200)
'''

class TestResourceListByKeyword(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourcesListByKeyword_get)
    def test_resource_list_by_keyword(self):
        hs = HydroShare(prompt_auth=False)
        res_list = hs.resources(subject="one,two,three")
        for (i, r) in enumerate(res_list):
            self.assertEquals(True, True)


class TestResourceListByBoundingBox(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourcesListByBoundingBox_get)
    def test_resource_list_by_bounding_box(self):
        hs = HydroShare(prompt_auth=False)

        res_list = hs.resources(coverage_type="box",
                                north="50",
                                south="30",
                                east="40",
                                west="20")
        for (i, r) in enumerate(res_list):
            self.assertEquals(True, True)


class TestReferencedFile(unittest.TestCase):
    @with_httmock(mocks.hydroshare.resourceCreateReferenceURL_post)
    def test_referenced_create(self):
        hs = HydroShare(prompt_auth=False)

        response = hs.createReferencedFile(pid='511debf8858a4ea081f78d66870da76c', path='data/contents', name='file.url',
                                           ref_url='https://www.hydroshare.org')

        self.assertEqual(response['status'], 'success')

    @with_httmock(mocks.hydroshare.resourceUpdateReferenceURL_post)
    def test_referenced_update(self):
        hs = HydroShare(prompt_auth=False)

        response = hs.updateReferencedFile(pid='511debf8858a4ea081f78d66870da76c', path='data/contents', name='file.url',
                                           ref_url='https://www.cuahsi.org')

        self.assertEqual(response['status'], 'success')

if __name__ == '__main__':
    unittest.main()
