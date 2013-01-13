import urllib2

def http_query(url, http_max_attempts=3):
    '''HTTP query, retries up to http_max_attempts until throwing an exception.'''
    attempts = 0
    while True:
        try:
            return urllib2.urlopen(url)
        except urllib2.HTTPError as e:
            attempts += 1
            if attempts >= http_max_attempts:
                raise e
