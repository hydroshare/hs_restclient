import json
import os

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from ..generators import resultsListGenerator


def default_progress_callback(monitor):
    pass


class BaseEndpoint(object):
    def __init__(self, hs):
        self.hs = hs


class ScimetaSubEndpoint(object):
    def __init__(self, hs, pid):
        self.hs = hs
        self.pid = pid

    def custom(self, payload):
        """

        :param payload:
            a key/value object containing the scimeta you want to store
            e.g. {"weather": "sunny", "temperature": "80C" }
        :return:
            empty (200 status code)
        """
        url = "{url_base}/resource/{pid}/scimeta/custom/".format(url_base=self.hs.url_base,
                                                                 pid=self.pid)
        r = self.hs._request('POST', url)
        return r


class FilesSubEndpoint(object):
    def __init__(self, hs, pid):
        self.hs = hs
        self.pid = pid

    def all(self):
        """
        :return:
            array of file objects (200 status code)
        """
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.hs.url_base,
                                                                 pid=self.pid)
        r = self.hs._request('GET', url)
        return r

    def metadata(self, file_id, params=None):
        """
        :params:
            title: string
            keywords: array
            extra_metadata: array
            temporal_coverage: coverage object
            spatial_coverage: coverage object

        :return:
            file metadata object (200 status code)
        """

        url_base = self.hs.url_base
        url = "{url_base}/resource/{pid}/files/{file_id}/metadata/".format(url_base=url_base,
                                                                           pid=self.pid,
                                                                           file_id=file_id)

        if params is None:
            r = self.hs._request('GET', url)
        else:
            headers = {}
            headers["Content-Type"] = "application/json"
            r = self.hs._request("PUT", url, data=json.dumps(params), headers=headers)

        return r

class FunctionsSubEndpoint(object):
    def __init__(self, hs, pid):
        self.hs = hs
        self.pid = pid

    def move_or_rename(self, payload):
        """
        Moves or renames a file

        :param payload:
            source_path: string
            target_path: string
        :return: (object)
            target_rel_path: tgt_path
        """
        url = "{url_base}/resource/{pid}/functions/move-or-rename/".format(
            url_base=self.hs.url_base,
            pid=self.pid)
        r = self.hs._request('POST', url, None, payload)
        return r

    def zip(self, payload):
        """
        Zips a resource file

        :param payload:
            input_coll_path: (string) input collection path
            output_zip_file_name: (string)
            remove_original_after_zip: (boolean)
        :return: (object)
            name: output_zip_fname
            size: size of the zipped file
            type: 'zip'
        """
        url = "{url_base}/resource/{pid}/functions/zip/".format(
            url_base=self.hs.url_base,
            pid=self.pid)
        r = self.hs._request('POST', url, None, payload)
        return r

    def unzip(self, payload):
        """
        Unzips a file

        :param payload:
            zip_with_rel_path: string
            remove_original_zip: boolean
        :return: (object)
            unzipped_path: string
        """
        zip_with_rel_path = payload.pop('zip_with_rel_path')

        url = "{url_base}/resource/{pid}/functions/unzip/{path}/".format(
            url_base=self.hs.url_base,
            path=zip_with_rel_path,
            pid=self.pid)
        r = self.hs._request('POST', url, None, payload)
        return r

    def rep_res_bag_to_irods_user_zone(self):
        """Replicate data bag to iRODS user zone.

        param payload:
            zip_with_rel_path: string
            remove_original_zip: boolean
        :return: (object)
            unzipped_path: string
        """
        url = "{url_base}/resource/{pid}/functions/rep-res-bag-to-irods-user-zone/".format(
            url_base=self.hs.url_base,
            pid=self.pid)
        r = self.hs._request('POST', url, None, {})
        return r

    def set_file_type(self, payload):
        """
        Sets a file to a specific HydroShare file type (e.g. NetCDF, GeoRaster, GeoFeature etc)

        :param payload:
            file_path: string (relative path of the file to be set to a specific file type)
            hs_file_type: string (one of the supported files types: NetCDF, GeoRaster and GeoFeature)
        :return: (object)
            message: string
        """
        file_path = payload.pop('file_path')
        hs_file_type = payload.pop('hs_file_type')

        url = "{url_base}/resource/{pid}/functions/set-file-type/{file_path}/{file_type}/".format(
            url_base=self.hs.url_base,
            pid=self.pid,
            file_path=file_path,
            file_type=hs_file_type)
        r = self.hs._request('POST', url, None, payload)
        return r


class ResourceEndpoint(BaseEndpoint):
    def __init__(self, hs, pid):
        super(ResourceEndpoint, self).__init__(hs)
        self.pid = pid
        self.scimeta = ScimetaSubEndpoint(hs, pid)
        self.functions = FunctionsSubEndpoint(hs, pid)
        self.files = FilesSubEndpoint(hs, pid)

    def copy(self):
        """Creates a copy of a resource.

        :return: string resource id
        """
        url = "{url_base}/resource/{pid}/copy/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)
        r = self.hs._request('POST', url)
        return r

    def flag(self, payload):
        """Set a single flag on a resource.

        :param payload:
            t: can be one of make_public, make_private, make_shareable,
            make_not_shareable, make_discoverable, make_not_discoverable
        :return:
            empty but with 202 status_code
        """
        url = "{url_base}/resource/{pid}/flag/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)

        r = self.hs._request('POST', url, None, payload)
        return r

    def files(self, payload):
        """Upload a file to a hydroshare resource.

        :param payload:
            file: File object to upload to server
            folder: folder path to upload the file to
        :return: json object
            resource_id: string resource id,
            file_name: string name of file
        """
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)

        encoder = MultipartEncoder({
            "file": (payload['file'], open(payload['file'], 'r')),
            "folder": payload['folder']
        })
        monitor = MultipartEncoderMonitor(encoder, default_progress_callback)

        r = self.hs._request('POST', url, None, data=monitor, headers={'Content-Type': monitor.content_type})
        return r.text

    def version(self):
        """Create a new version of a resource.

        :return: resource id (string)
        """
        url = "{url_base}/resource/{pid}/version/".format(url_base=self.hs.url_base,
                                                          pid=self.pid)
        r = self.hs._request('POST', url)
        return r

    def public(self, boolean):
        """Pass through helper function for flag function."""
        if(boolean):
            r = self.flag({
                "flag": "make_public"
            })
        else:
            r = self.flag({
                "flag": "make_private"
            })

        return r

    def discoverable(self, boolean):
        """Pass through helper function for flag function."""
        if(boolean):
            r = self.flag({
                "flag": "make_discoverable"
            })
        else:
            r = self.flag({
                "flag": "make_not_discoverable"
            })

        return r

    def shareable(self, boolean):
        """Pass through helper function for flag function."""
        if(boolean):
            r = self.flag({
                "flag": "make_shareable"
            })
        else:
            r = self.flag({
                "flag": "make_not_shareable"
            })

        return r



class ResourceList(BaseEndpoint):
    def __init__(self, hs, **kwargs):
        super(ResourceList, self).__init__(hs)

        """
        Query the GET /hsapi/resource/ REST end point of the HydroShare server.

        :param creator: Filter results by the HydroShare user name of resource creators
        :param owner: Filter results by the HydroShare user name of resource owners
        :param user: Filter results by the HydroShare user name of resource users (i.e. owner, editor, viewer, public
            resource)
        :param group: Filter results by the HydroShare group name associated with resources
        :param from_date: Filter results to those created after from_date.  Must be datetime.date.
        :param to_date: Filter results to those created before to_date.  Must be datetime.date.  Because dates have
            no time information, you must specify date+1 day to get results for date (e.g. use 2015-05-06 to get
            resources created up to and including 2015-05-05)
        :param types: Filter results to particular HydroShare resource types.  Must be a sequence type
            (e.g. list, tuple, etc.), but not a string.
        :param start: Filter results by start
        :param count: Filter results by count
        :param subject: Filter by comma separated list of subjects
        :param metadata: Filter by JSON metadata
        :param full_text_search: Filter by full text search
        :param edit_permission: Filter by boolean edit permission
        :param published: Filter by boolean published status
        :param coverage_type: Filter by coverage type, one of 'box' or 'point'
        :param north: Filter by north coordinate, float or char
        :param south: Filter by south coordinate, float or char
        :param east: Filter by east coordinate, float or char
        :param west: Filter by west coordinate, float or char

        :raises: HydroShareHTTPException to signal an HTTP error
        :raises: HydroShareArgumentException for any invalid arguments

        :return: A generator that can be used to fetch dict objects, each dict representing
            the JSON object representation of the resource returned by the REST end point.  For example:

        >>> for resource in hs.getResourceList():
        >>>>    print resource
         {u'bag_url': u'http://www.hydroshare.org/static/media/bags/e62a438bec384087b6c00ddcd1b6475a.zip',
          u'creator': u'B Miles',
          u'date_created': u'05-05-2015',
          u'date_last_updated': u'05-05-2015',
          u'resource_id': u'e62a438bec384087b6c00ddcd1b6475a',
          u'resource_title': u'My sample DEM',
          u'resource_type': u'RasterResource',
          u'discoverable': True,
          u'shareable': True,
          u'immutable': True,
          u'published': True,
          u'resource_url': u'http://www.hydroshare.org/resource/e62a438bec384087b6c00ddcd1b6475a/',
          u'resource_map_url': u'http://www.hydroshare.org/resource/e62a438bec384087b6c00ddcd1b6475a/map/',
          u'science_metadata_url': u'http://www.hydroshare.org/hsapi/scimeta/e62a438bec384087b6c00ddcd1b6475a/',
          u'public': True}
         {u'bag_url': u'http://www.hydroshare.org/static/media/bags/hr3hy35y5ht4y54hhthrtg43w.zip',
          u'creator': u'B Miles',
          u'date_created': u'01-02-2015',
          u'date_last_updated': u'05-13-2015',
          u'resource_id': u'hr3hy35y5ht4y54hhthrtg43w',
          u'resource_title': u'Other raster',
          u'resource_type': u'RasterResource',
          u'discoverable': True,
          u'shareable': True,
          u'immutable': True,
          u'published': True,
          u'resource_url': u'http://www.hydroshare.org/resource/hr3hy35y5ht4y54hhthrtg43w/',
          u'resource_map_url': u'http://www.hydroshare.org/resource/hr3hy35y5ht4y54hhthrtg43w/map/',
          u'science_metadata_url': u'http://www.hydroshare.org/hsapi/scimeta/hr3hy35y5ht4y54hhthrtg43w/',
          u'public': True}


          Filtering (have):

          /hsapi/resourceList/?from_date=2015-05-03&to_date=2015-05-06
          /hsapi/resourceList/?user=admin
          /hsapi/resourceList/?owner=admin
          /hsapi/resourceList/?creator=admin
          /hsapi/resourceList/?group=groupname
          /hsapi/resourceList/?types=GenericResource&types=RasterResource

          Filtering (need):

          /hsapi/resourceList/?sharedWith=user

        """
        url = "{url_base}/resource/".format(url_base=self.hs.url_base)

        params = kwargs
        if 'from_date' in kwargs:
            params['from_date'] = kwargs['from_date'].strftime('%Y-%m-%d')
        if 'to_date' in kwargs:
            params['to_date'] = kwargs['to_date'].strftime('%Y-%m-%d')
        if 'types' in kwargs:
            params['type'] = kwargs.pop('types')

        self.list = resultsListGenerator(self.hs, url, params)