"""
Mocks for HydroShare REST API client library tests.

Adapted from: http://www.appneta.com/blog/python-unit-test-mock/

"""
import os

from httmock import response, urlmatch


NETLOC = r'www\.hydroshare\.org$'
HEADERS = {'content-type': 'application/json'}
GET = 'get'


class Resource:
    """ A HydroShare resource.
    :param path: The file path to the resource.
    """

    def __init__(self, path):
        self.path = path

    def get(self):
        """ Perform a GET request on the resource.
        :rtype: str
        """
        with open(self.path, 'r') as f:
            content = f.read()
        return content


@urlmatch(netloc=NETLOC, method=GET)
def resourceTypes_get(url, request):
    file_path = url.netloc + url.path
    # Remove trailing slash so that we can open the file
    file_path = file_path.strip('/')
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=GET)
def resourceList_get(url, request):
    if url.query == '':
        file_path = url.netloc + url.path + 'resourceList-1'
    elif url.query == 'page=2':
        file_path = url.netloc + url.path + 'resourceList-2'
    else:
        file_path = '';
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=GET)
def resourceListFilterCreator_get(url, request):
    if url.query == 'creator=bmiles':
        file_path = url.netloc + url.path + 'resourceList-bmiles'
    else:
        file_path = '';
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=GET)
def resourceListFilterDate_get(url, request):
    if url.query == 'from_date=2015-05-20':
        file_path = url.netloc + url.path + 'resourceList-from_date'
    elif url.query == 'to_date=2015-05-21':
        file_path = url.netloc + url.path + 'resourceList-to_date'
    elif url.query == 'from_date=2015-05-19&to_date=2015-05-22':
        file_path = url.netloc + url.path + 'resourceList-from_date-to_date'
    else:
        file_path = '';
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)