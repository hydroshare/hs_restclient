"""
Mocks for HydroShare REST API client library tests.

Adapted from: http://www.appneta.com/blog/python-unit-test-mock/

"""
import os
from urlparse import parse_qs

from httmock import response, urlmatch


NETLOC = r'www\.hydroshare\.org$'
HEADERS = {'content-type': 'application/json'}
GET = 'get'
POST = 'post'
PUT = 'put'
DELETE = 'delete'


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
        file_path = ''
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
        file_path = ''
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
        file_path = ''
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
        file_path = ''
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
        if url.path == '/hsapi/resource/types':
            file_path = url.netloc + url.path
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/')
            response_status = 200
        if url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/sysmeta/':
            file_path = url.netloc + url.path + '511debf8858a4ea081f78d66870da76c'
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/')
            response_status = 200
        if url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/':
            file_path = url.netloc + url.path
            # Remove trailing slash so that we can open the file
            file_path = file_path.strip('/') + '.zip'
            HEADERS['content-type'] = 'application/zip'
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
        if url.path == '/hsapi/resource/511debf8858a4ea081f78d66870da76c/sysmeta/':
            file_path = url.netloc + url.path + '511debf8858a4ea081f78d66870da76c'
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
def scimeta_xml_get(url, request):
    file_path = url.netloc + url.path + 'scimeta.xml'

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=GET)
def scimeta_json_get(url, request):
    file_path = url.netloc + url.path + '/scimeta-get-response'

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=PUT)
def scimeta_json_put(url, request):
    file_path = url.netloc + url.path + '/scimeta-update-response'

    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(202, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=GET)
def resourcemap_get(url, request):
    file_path = url.netloc + url.path + 'resourcemap.xml'

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
        file_path = ''
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=GET)
def resourceFolderContents_get(url, request):
    file_path = url.netloc + url.path + 'folder-content-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=PUT)
def resourceFolderCreate_put(url, request):
    file_path = url.netloc + url.path + 'create-folder-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(201, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=DELETE)
def resourceFolderDelete_delete(url, request):
    file_path = url.netloc + url.path + 'delete-folder-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceCopy_post(url, request):
    file_path = url.netloc + url.path + 'copy-1'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(202, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceVersion_post(url, request):
    file_path = url.netloc + url.path + 'version-1'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(202, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceFlags_post(url, request):
    body = parse_qs(request.body)
    file_path = url.netloc + url.path + body.get('t')[0]
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(202, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceScimetaCustom_post(url, request):
    file_path = url.netloc + url.path + 'custom-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceMoveFileOrFolder_post(url, request):
    file_path = url.netloc + url.path + 'move-or-rename-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)

@urlmatch(netloc=NETLOC, method=POST)
def resourceZipFolder_post(url, request):
    file_path = url.netloc + url.path + 'zip-folder-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceUnzipFile_post(url, request):
    file_path = url.netloc + url.path + 'unzip-file-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceUploadFile_post(url, request):
    file_path = url.netloc + url.path + 'upload-file-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=GET)
def resourcesListByKeyword_get(url, request):
    file_path = url.netloc + url.path + 'resourceList-keyword'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=GET)
def resourcesListByBoundingBox_get(url, request):
    file_path = url.netloc + url.path + 'resourceList-bounding-box'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=POST)
def resourceSetFileType_post(url, request):
    file_path = url.netloc + url.path + '/set-file-type-response'
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(202, content, HEADERS, None, 5, request)


@urlmatch(netloc=NETLOC, method=GET)
def resourceCreateTicket_get(url, request):
    resource_id = '28f87079ceaf440588e7866a0f4b6c57'
    end_of_url = "resource/{}/ticket/bag/"\
        .format(resource_id) 
    content = {
        u'operation': u'read',
        u'path': u'/hydroshareZone/home/cuahsi2DataProxy/bags/28f87079ceaf440588e7866a0f4b6c57.zip',
        u'resource_id': u'28f87079ceaf440588e7866a0f4b6c57',
        u'ticket_id': u'pwYwPanpnwdDZa9'
    }
    if url.path.endswith(end_of_url): 
        return response(201, content, HEADERS, None, 5, request) 
    else: 
        return response(403, "Insufficient permission",  
                        {'content-type': 'application/json'}, None, 5, request) 


@urlmatch(netloc=NETLOC, method=GET)
def resourceListTicket_get(url, request):
    resource_id = '28f87079ceaf440588e7866a0f4b6c57'
    ticket_id = 'pwYwPanpnwdDZa9'
    end_of_url = "resource/{}/ticket/info/{}/"\
        .format(resource_id, ticket_id) 
    content = {
        u'expires': u'2017-07-26.00:17:00',
        u'filename': u'28f87079ceaf440588e7866a0f4b6c57.zip',
        u'full_path':
         u'/hydroshareZone/home/hydroDataProxy/bags/28f87079ceaf440588e7866a0f4b6c57.zip',
        u'id': u'457392',
        u'obj type': u'data',
        u'owner': u'hydroDataProxy',
        u'ticket_id': u'pwYwPanpnwdDZa9',
        u'type': u'read',
        u'uses count': u'0',
        u'uses limit': u'1',
        u'write byte count': u'0',
        u'write byte limit': u'0',
        u'write file count': u'0',
        u'write file limit': u'10',
        u'zone': u'hydroshareZone'
    }
    if url.path.endswith(end_of_url): 
        return response(200, content, HEADERS, None, 5, request) 
    else: 
        # mimic one kind of error
        return response(403, "Insufficient permission",  
                        {'content-type': 'application/json'}, None, 5, request) 


@urlmatch(netloc=NETLOC, method=DELETE)
def resourceDeleteTicket_delete(url, request):
    resource_id = '28f87079ceaf440588e7866a0f4b6c57'
    ticket_id = 'pwYwPanpnwdDZa9'
    end_of_url = "resource/{}/ticket/info/{}/"\
        .format(resource_id, ticket_id) 
    content = {
        u'expires': u'2017-07-26.00:17:00',
        u'filename': u'28f87079ceaf440588e7866a0f4b6c57.zip',
        u'full_path':
         u'/hydroshareZone/home/hydroDataProxy/bags/28f87079ceaf440588e7866a0f4b6c57.zip',
        u'id': u'457392',
        u'obj type': u'data',
        u'owner': u'hydroDataProxy',
        u'ticket_id': u'pwYwPanpnwdDZa9',
        u'type': u'read',
        u'uses count': u'0',
        u'uses limit': u'1',
        u'write byte count': u'0',
        u'write byte limit': u'0',
        u'write file count': u'0',
        u'write file limit': u'10',
        u'zone': u'hydroshareZone'
    }
    if url.path.endswith(end_of_url): 
        return response(200, content, HEADERS, None, 5, request) 
    else: 
        return response(403, "Insufficient permission",  
                        {'content-type': 'text/plain'}, None, 5, request) 
