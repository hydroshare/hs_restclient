
def copy(hs, pid):
    url = "{url_base}/resource/{pid}/copy/".format(url_base=hs.url_base,
                                                   pid=pid)
    r = hs._request('POST', url)
    return r

def version(hs, pid):
    url = "{url_base}/resource/{pid}/version/".format(url_base=hs.url_base,
                                                   pid=pid)
    r = hs._request('POST', url)
    return r
