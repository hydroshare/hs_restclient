from .functions import copy, version

class ResourceEndpoint(object):
    def __init__(self, hs_object):
        self.hs = hs_object

    def copy(self, pid):
        return copy(self.hs, pid)

    def version(self, pid):
        return version(self.hs, pid)