class BaseEndpoint(object):
    def __init__(self, hs):
        self.hs = hs


class ScimetaSubEndpoint(object):
    def __init__(self, hs, pid):
        self.hs = hs
        self.pid = pid

    def custom(self, payload):
        url = "{url_base}/resource/{pid}/scimeta/custom/".format(url_base=self.hs.url_base,
                                                                 pid=self.pid)
        r = self.hs._request('POST', url)
        return r


class FunctionsSubEndpoint(object):
    def __init__(self, hs, pid):
        self.hs = hs
        self.pid = pid

    def move_or_rename(self, payload):
        url = "{url_base}/resource/{pid}/functions/move-or-rename/".format(
            url_base=self.hs.url_base,
            pid=self.pid)
        r = self.hs._request('POST', url, None, payload)
        return r

    def zip(self, payload):
        url = "{url_base}/resource/{pid}/functions/zip/".format(
            url_base=self.hs.url_base,
            pid=self.pid)
        r = self.hs._request('POST', url, None, payload)
        return r

    def unzip(self, payload):
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
        url = "{url_base}/resource/{pid}/copy/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)
        r = self.hs._request('POST', url)
        return r

    def files(self, payload):
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)

        r = self.hs._request('POST', url, None, payload)
        return r

    def flag(self, payload):
        url = "{url_base}/resource/{pid}/flag/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)

        r = self.hs._request('POST', url, None, payload)
        return r

    def scimeta(self, payload=None):
        return ScimetaSubEndpoint(self.hs, self.pid)

    def version(self):
        url = "{url_base}/resource/{pid}/version/".format(url_base=self.hs.url_base,
                                                          pid=self.pid)
        r = self.hs._request('POST', url)
        return r
