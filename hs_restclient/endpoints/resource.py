class ResourceEndpoint(object):
    def __init__(self, hs, pid):
        self.hs = hs
        self.pid = pid

    def copy(self):
        url = "{url_base}/resource/{pid}/copy/".format(url_base=self.hs.url_base,
                                                       pid=self.pid)
        r = self.hs._request('POST', url)
        return r

    def version(self):
        url = "{url_base}/resource/{pid}/version/".format(url_base=self.hs.url_base,
                                                          pid=self.pid)
        r = self.hs._request('POST', url)
        return r
