class HydroShareException(Exception):
    def __init__(self, args):
        super(HydroShareException, self).__init__(args)


class HydroShareArgumentException(HydroShareException):
    def __init__(self, args):
        super(HydroShareArgumentException, self).__init__(args)


class HydroShareBagNotReadyException(HydroShareException):
    def __init__(self, args):
        super(HydroShareBagNotReadyException, self).__init__(args)


class HydroShareNotAuthorized(HydroShareException):
    def __init__(self, args):
        super(HydroShareNotAuthorized, self).__init__(args)
        self.method = args[0]
        self.url = args[1]

    def __str__(self):
        msg = "Not authorized to perform {method} on {url}."
        return msg.format(method=self.method, url=self.url)

    def __unicode__(self):
        return str(self)


class HydroShareNotFound(HydroShareException):
    def __init__(self, args):
        super(HydroShareNotFound, self).__init__(args)
        self.pid = args[0]
        if len(args) >= 2:
            self.filename = args[1]
        else:
            self.filename = None

    def __str__(self):
        if self.filename:
            msg = "File '{filename}' was not found in resource '{pid}'."
            msg = msg.format(filename=self.filename, pid=self.pid)
        else:
            msg = "Resource '{pid}' was not found."
            msg = msg.format(pid=self.pid)
        return msg

    def __unicode__(self):
        return str(self)


class HydroShareHTTPException(HydroShareException):
    """ Exception used to communicate HTTP errors from HydroShare server

        Arguments in tuple passed to constructor must be: (url, status_code, params).
        url and status_code are of type string, while the optional params argument
        should be a dict.
    """
    def __init__(self, response):
        super(HydroShareHTTPException, self).__init__(response)
        self.url = response.request.url
        self.method = response.request.method
        self.status_code = response.status_code
        self.status_msg = response.text if response.text else "No status message"

    def __str__(self):
        msg = "Received status {status_code} {status_msg} when accessing {url} " + \
              "with method {method}."
        return msg.format(status_code=self.status_code,
                          status_msg=self.status_msg,
                          url=self.url,
                          method=self.method)

    def __unicode__(self):
        return str(self)


class HydroShareAuthenticationException(HydroShareException):
    def __init__(self, args):
        super(HydroShareArgumentException, self).__init__(args)
