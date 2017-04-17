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
        url = "{url_base}/resource/{pid}/functions/unzip/".format(
            url_base=self.hs.url_base,
            pid=self.pid)
        r = self.hs._request('POST', url, None, payload)
        return r

class ResourceEndpoint(BaseEndpoint):
    def __init__(self, hs, pid):
        super(ResourceEndpoint, self).__init__(hs)
        self.pid = pid
        self.scimeta = ScimetaSubEndpoint(hs, pid)
        self.functions = FunctionsSubEndpoint(hs, pid)

    def copy(self):
        """
        Creates a copy of a resource

        :return: string resource id
        """
        url = "{url_base}/resource/{pid}/copy/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)
        r = self.hs._request('POST', url)
        return r

    def files(self, payload):
        """
        Uploads a file to a hydroshare resource

        :param payload:
            file: File object to upload to server
            folder: folder path to upload the file to
        :return: json object
            resource_id: string resource id,
            file_name: string name of file
        """
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)

        r = self.hs._request('POST', url, None, payload)
        return r

    def flag(self, payload):
        """
        Sets a single flag on a resource

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

    def version(self):
        """
        Creates a new version of a resource

        :return: resource id (string)
        """
        url = "{url_base}/resource/{pid}/version/".format(url_base=self.hs.url_base,
                                                          pid=self.pid)
        r = self.hs._request('POST', url)
        return r
