from utilities import http_query
import datetime
import hashlib
import joblib
import os.path
import re
import simplejson as json
import urllib
import yaml

def film_revision_scrape(films, output_dir, horizon_start=0, horizon_end=28, 
                         http_max_attempts=3, verbose=False):
    
    for i in films.index:
        film = films.ix[i]
        if film['wiki_title'] is not None:
            revisions = film_revisions(film, horizon_start, horizon_end, 
                                       http_max_attempts=http_max_attempts,
                                       verbose=verbose)
            if verbose:
                print '(%d) %s / %d revisions' % (i, film['wiki_title'], len(revisions))
            filename = '%s.revisions' % hashlib.md5(film['wiki_title'].encode('utf-8')).hexdigest()
            filename = os.path.join(output_dir, filename)
            joblib.dump(revisions, filename)
        else:
            raise Exception('Error: no wiki_title found for film %s, index %i' % (film['title'], i))

def film_revisions(film, horizon_start=0, horizon_end=28, http_max_attempts=3, verbose=False):
    
    all_revisions = []
    api_params = { 'format': 'json', 
                   'action': 'query',
                   'redirects': None,
                   'prop': 'revisions',
                   'rvlimit': 500,
                   'rvdir': 'older',
                   'rvprop': ['ids', 'user', 'userid', 'timestamp', 'flags', 'comment', 'size', 'content'],
                   'titles': urllib.quote(film['wiki_title'].encode('utf-8')),
                   'rvstart': mediawiki_timestamp(film['opening_date'] - datetime.timedelta(days=horizon_start)),
                   'rvend': mediawiki_timestamp(film['opening_date'] - datetime.timedelta(days=horizon_end)),
                  }
    
    while True:
        query_result = wikipedia_api(api_params, http_max_attempts=http_max_attempts)
        pages = query_result['query']['pages']
        if len(pages) < 1 or pages.keys()[0] == -1:
            raise Exception('No Wikipedia page found for %s' % title)
        if 'revisions' not in pages.items()[0][1]:  # no revisions, or article did not exist
            break
        revisions = pages.items()[0][1]['revisions']
        all_revisions.extend(revisions)
        if 'query-continue' in query_result:
            if 'rvstart' in api_params:   # first call uses rvstart, the rest use rvstartid
                del api_params['rvstart']
            api_params['rvstartid'] = query_result['query-continue']['revisions']['rvcontinue']
        else:
            break
        
    return all_revisions

def attach_wikipedia_titles(films, config_file=None, http_max_attempts=3, verbose=False):
    
    if config_file is not None:
        config = yaml.load(open(config_file, 'r').read())
    else:
        config = {}
    
    wiki_titles = []
    for i in films.index:
        film = films.ix[i]
        (title, year) = (film['title'], film['year'])
        title_year = '%s (%d)' % (title, year)
        if 'title_override' in config and title_year in config['title_override']:
            wiki_title = config['title_override'][title_year]
        else:
            wiki_title = retrieve_wikipedia_title(films.ix[i], http_max_attempts=http_max_attempts)
        if verbose: 
            if wiki_title is not None:
                clean_wiki_title = re.sub(' \((\d{4} ){0,1}film\)$', '', wiki_title)
                if clean_wiki_title.lower() != title.lower():
                    print('W: Retrieved %s for %s' % (wiki_title, title))
            else:
                print('W: No Wikipedia article found for %s' % title)
        wiki_titles.append(wiki_title)
    films['wiki_title'] = wiki_titles
    return films

def retrieve_wikipedia_title(film, search_limit=15, http_max_attempts=3):
    '''
    Given film data (a dictionary with 'title' and 'year' or other data 
    structure that supports this indexing), attempts to retrieve the title of
    the Wikipedia article about this film. Accuracy is decent but not 100%, 
    does the best it can. Returns the title, or None if nothing found. 
    '''
    
    # Note: Wikipedia won't return more than 15 hits, so there's no point in
    # setting search_limit > 15. 
    
    year_film_re = re.compile(r'\(%d film\)$' % film['year'])
    film_re = re.compile(r'\(film\)$')
    query_params = { 'format': 'json',
                     'action': 'opensearch',
                     'search': urllib.quote(film['title'].encode('utf-8')),
                     'limit': search_limit }
    query_result = wikipedia_api(query_params, http_max_attempts=http_max_attempts)
    hits = query_result[1]
    
    # easy cases first
    
    if len(hits) == 0:
        page = None 
    elif len(hits) == 1:
        page = hits[0]
    else:
        
        # First try to find a year-specific match, like "Alice in 
        # Wonderland (2010 film)"
        
        year_film_matches = find_re_matches(year_film_re, hits)
        if len(year_film_matches) >= 1:
            page = year_film_matches[0]
        else:
            
            # Now try for just the film label, like "Shutter Island (film)"
            
            film_matches = find_re_matches(film_re, hits)
            if len(film_matches) >= 1:
                page = film_matches[0]
            else:
                
                # Are there a suspiciously large number of hits? If so, you may
                # have a generic title that returns lots of hits, like "The 
                # American", where "The American (2012 film)" doesn't place in 
                # the top 15. Try directly querying w/the label appended. 
                
                if len(hits) == search_limit:
                    query_params['search'] = (urllib.quote(film['title'].encode('utf-8') + (' (%d film)' % film['year'])))
                    query_result2 = wikipedia_api(query_params, http_max_attempts=http_max_attempts)
                    hits2 = query_result2[1]
                    if len(hits2) > 0:
                        page = hits2[0]
                    else:
                        query_params['search'] = (urllib.quote(film['title'].encode('utf-8') + ' (film)'))
                        query_result3 = wikipedia_api(query_params, http_max_attempts=http_max_attempts)
                        hits3 = query_result3[1]
                        if len(hits3) > 0:
                            page = hits3[0]
                        else:
                            page = hits[0] # Just go with the first hit at this point
                
                else:
                    page = hits[0]  # Just go with the first hit at this point
    
    return page

def find_re_matches(regexp, hits):
    '''Finds matches for regexp in hits'''
    matches = []
    for hit in hits:
        if regexp.search(hit) is not None:
            matches.append(hit)
    return matches

def wikipedia_api(arg_dict, http_max_attempts=3):
    api_url = r'http://en.wikipedia.org/w/api.php?'
    url_args = []
    for key in arg_dict:
        if arg_dict[key] is None:
            url_args.append('%s' % key)
        elif isinstance(arg_dict[key], list):
            url_args.append('%s=%s' % (key, '|'.join(arg_dict[key])))
        else:
            url_args.append('%s=%s' % (key, arg_dict[key]))
    api_url += '&'.join(url_args)
    return json.loads(http_query(api_url, http_max_attempts=http_max_attempts).read())

def mediawiki_timestamp(dt):
    if not isinstance(dt, datetime.datetime):
        return '%04d%02d%02d000000' % (dt.year, dt.month, dt.day)
    else:
        return '%04d%02d%02d%02d%02d%02d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def load_wikipedia_revisions(film, output_dir):
    filename = '%s.revisions' % hashlib.md5(film['wiki_title'].encode('utf-8')).hexdigest()
    filename = os.path.join(output_dir, filename)
    if not os.path.isfile(filename):
        raise Exception('Error: expected file %s not found for %s' % (filename, film['wiki_title']))
    revisions = joblib.load(filename)
    for rev in revisions:
        if 'timestamp' in rev:
            rev['timestamp'] = datetime.datetime.strptime(rev['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
    return revisions