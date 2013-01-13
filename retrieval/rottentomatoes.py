from utilities import http_query
import difflib
import re
import simplejson as json
import urllib
import yaml

def attach_rt_data(films, api_key=None, config_file=None, http_max_attempts=3,
                   verbose=False):
    
    if config_file is not None:
        config = yaml.load(open(config_file, 'r').read())
    else:
        config = {}
    
    if api_key is not None:
        config['api_key'] = api_key
    if config['api_key'] is None:
        raise Exception('Either api_key or a config_file with an API key must be specified')
    
    all_rt_data = { 'mpaa_rating': [],
                    'runtime': [],
                    'genres': [],
                    'imdb_id': [],
                    'rt_id': [],
                    'directors': [],
                    'actors': [],
                  }
    
    if 'id_override' in config:
        id_override = config['id_override']
    else:
        id_override = {}
    
    for i in films.index:
        film = films.ix[i]
        (title, year) = (film['title'], film['year'])
        title_year = '%s (%d)' % (title, year)
        if title_year in id_override:
            rt_id = id_override[title_year]
        else:
            # Get the best search hit first, then query by id. Why not just use
            # search data? Because genres are missing from search query data
            # alone, sadly - you have to make a direct query for the film by id
            # to get them. 
            try:
                rt_search_data = film_search_best_hit(film['title'], film['year'], 
                                                      api_key=config['api_key'], 
                                                      http_max_attempts=http_max_attempts,
                                                      verbose=verbose)
                rt_id = rt_search_data['id']
            except:
                if verbose:
                    print('RT: No film ID matched to %s (%s)' % (film['title'], film['year']))
                rt_id = None
        
        if rt_id is not None:
            try:
                rt_data = film_info(rt_id, config['api_key'], http_max_attempts=http_max_attempts)
            except:
                rt_data = {}
            # verbose mode gives a heads-up if the title wasn't a precise match        
            if verbose and re.sub('\W', '', rt_data['title']).lower() != re.sub('\W', '', title).lower():
                print('RT: Using %s for %s (%s)' % (rt_data['title'], title, year))
        else:
            rt_data = {}
        
        try: all_rt_data['mpaa_rating'].append(rt_data['mpaa_rating'])
        except: all_rt_data['mpaa_rating'].append(None)
        try: all_rt_data['runtime'].append(int(rt_data['runtime']))
        except: all_rt_data['runtime'].append(None)
        try: all_rt_data['genres'].append(','.join(rt_data['genres']))
        except: all_rt_data['genres'].append(None)
        try: all_rt_data['rt_id'].append(rt_data['id'])
        except: all_rt_data['rt_id'].append(None)
        try: all_rt_data['imdb_id'].append(rt_data['alternate_ids']['imdb'])
        except: all_rt_data['imdb_id'].append(None)
        
        try:
            directors = []
            for director in rt_data['abridged_directors']:
                if 'name' in director:
                    directors.append(director['name'])
            all_rt_data['directors'].append(','.join(directors))
        except:
            all_rt_data['directors'].append(None)
        try:
            actors = []
            for actor in rt_data['abridged_cast']:
                if 'name' in actor:
                    actors.append(actor['name'])
            all_rt_data['actors'].append(','.join(actors))
        except:
            all_rt_data['actors'].append(None)
    
    for col in all_rt_data:
        films[col] = all_rt_data[col]
    
    return films

def film_info(id, api_key, http_max_attempts=3):
    
    rt_query = r'http://api.rottentomatoes.com/api/public/v1.0/movies/%s.json' % id
    rt_url = '%s?apikey=%s' % (rt_query, api_key)
    return json.loads(http_query(rt_url, http_max_attempts=http_max_attempts).read())

def search_by_title(title, api_key, http_max_attempts=3):
    
    rt_query = r'http://api.rottentomatoes.com/api/public/v1.0/movies.json'
    rt_url = '%s?apikey=%s&q=%s' % (rt_query, api_key, urllib.quote(title.encode('utf-8')))
    return json.loads(http_query(rt_url, http_max_attempts=http_max_attempts).read())

def film_search_best_hit(title, year, api_key, http_max_attempts=3, verbose=False):
    
    year = int(year)
    
    search_data = search_by_title(title, api_key, http_max_attempts=http_max_attempts)
    if 'error' in search_data:
        raise Exception('Rotten Tomatoes API returned error: %s' % search_data['error'])
    
    hits = []
    for search_hit in search_data['movies']:
        try:
            search_hit_release_date = search_hit['release_dates']['theater']
            search_hit_year = int(search_hit_release_date[0:4])  # it's in 'YYYY-MM-DD' format
            if year - search_hit_year <= 1:  # sometimes they differ by a year, small/non-US earlier release on RT
                hits.append(search_hit)
        except:
            pass
    if len(hits) == 0:
        if verbose:
            print('RT: No hits for %s (%s)' % (title, year))
        return None
    else:
        hits_by_title = { x['title']: x for x in hits }
        hit_titles_sorted = difflib.get_close_matches(title, hits_by_title.keys(), cutoff=0)
        hit_top_title = hit_titles_sorted[0]
        return hits_by_title[hit_top_title]
