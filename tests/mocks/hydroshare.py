"""
Mocks for HydroShare REST API client library tests.

Adapted from: http://www.appneta.com/blog/python-unit-test-mock/

"""
import os

from httmock import response, urlmatch


NETLOC = r'www\.hydroshare\.org$'
HEADERS = {'content-type': 'application/json'}
GET = 'get'
POST = 'post'
PUT = 'put'


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
        with open(self.path, 'rb') as f:
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

@urlmatch(netloc=NETLOC, method=GET)
def resourceListFilterType_get(url, request):
    if url.query == 'type=RasterResource':
        file_path = url.netloc + url.path + 'resourceList-type'
    else:
        file_path = '';
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC)
def createResourceCRUD(url, request):
    file_path = None
    # This gets tricky.  HydroShare.createResource() can implicitly
    # call HydroShare.getResourceTypes(), so we need to handle those requests too
    if request.method == 'GET':
        if url.path == '/hsapi/resourceTypes/':
            file_path = url.netloc + url.path
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/')
            response_status = 200
        if url.path == '/hsapi/sysmeta/511debf8858a4ea081f78d66870da76c/':
            file_path = url.netloc + url.path
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/')
            response_status = 200
        if url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/':
            file_path = url.netloc + url.path
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/') + '.zip'
            response_status = 200
    elif request.method == 'POST' and url.path == '/hsapi/resource/':
        file_path = url.netloc + url.path + 'create-response'
        response_status = 201
    elif request.method == 'DELETE' and url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/':
        file_path = url.netloc + url.path + 'delete-response'
        response_status = 200
    else:
        file_path = ''

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(response_status, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC)
def resourceFileCRUD(url, request):
    file_path = None
    if request.method == 'GET':
        if url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/files/another_resource_file.txt':
            file_path = url.netloc + url.path
            response_status = 200
    elif request.method == 'POST' and url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/files/':
            file_path = url.netloc + url.path + 'add-response'
            response_status = 201
    elif request.method == 'DELETE' and url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/files/another_resource_file.txt':
        path = os.path.dirname(url.path)
        file_path = url.netloc + path + '/' + 'delete-response'
        response_status = 200
    else:
        file_path = ''

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(response_status, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC)
def accessRules_put(url, request):
    if request.method == 'PUT':
        if request.body == 'public=True':
            file_path = url.netloc + url.path + 'makepublic-response'
        else:
            file_path = ''
    elif request.method == 'GET':
        if url.path == '/hsapi/sysmeta/511debf8858a4ea081f78d66870da76c/':
            file_path = url.netloc + url.path
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/') + '-public'
    else:
        file_path = ''
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=GET)
def userInfo_get(url, request):
    file_path = url.netloc + url.path + 'userInfo-1'

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=GET)
def scimeta_get(url, request):
    file_path = url.netloc + url.path + 'scimeta.xml'

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=GET)
def resourceFileList_get(url, request):
    if url.query == '':
        file_path = url.netloc + url.path + 'file_list-1'
    elif url.query == 'page=2':
        file_path = url.netloc + url.path + 'file_list-2'
    else:
        file_path = '';
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)
