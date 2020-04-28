from .exceptions import HydroShareNotAuthorized, HydroShareNotFound, HydroShareHTTPException

def resultsListGenerator(hs, url, params=None):
    # Get first (only?) page of results
    r = hs._request('GET', url, params=params)
    if r.status_code != 200:
        if r.status_code == 403:
            raise HydroShareNotAuthorized(('GET', url))
        elif r.status_code == 404:
            raise HydroShareNotFound((url,))
        else:
            raise HydroShareHTTPException(r)
    res = r.json()
    results = res['results']
    for item in results:
        yield item

    # Get remaining pages (if any exist)
    while res['next']:
        next_url = res['next']
        if hs.use_https:
            # Make sure the next URL uses HTTPS
            next_url = next_url.replace('http://', 'https://', 1)
        r = hs._request('GET', next_url, params=params)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', next_url))
            elif r.status_code == 404:
                raise HydroShareNotFound((next_url,))
            else:
                raise HydroShareHTTPException(r)
        res = r.json()
        results = res['results']
        for item in results:
            yield item