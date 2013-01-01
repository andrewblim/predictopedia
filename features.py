from bs4 import BeautifulSoup
import datetime
import hashlib
import joblib
import numpy as np
import os.path
import pandas as pd
import re
import simplejson as json
import urllib
import urllib2

def common_films(films, min_common=3, max_days_apart=1825, verbose=False):
    
    members = {}
    similar_indices = [list() for i in range(len(films))]
    similar_titles = [list() for i in range(len(films))]
    
    for i in films.index:
        film = films.ix[i]
        members[i] = set()
        if pd.notnull(film['directors']):
            members[i] |= set([film['directors']])  # don't split - treat directing duos as one
        if pd.notnull(film['actors']):
            members[i] |= set(film['actors'].split(','))
    
    for i in range(len(films.index)):
        
        film1 = films.ix[films.index[i]]
        for j in range(i+1, len(films.index)):
            
            film2 = films.ix[films.index[j]]
            members1 = members[i]
            members2 = members[j]
            
            # similar if there are at least a certain number of common people
            # and if they were not released too far apart (default 3 common
            # people, 1825 days = 5 years)
            
            datediff = film1['opening_date'] - film2['opening_date']
            if len(members1 & members2) >= min_common and abs(datediff.days) <= max_days_apart:
                if datediff.days > 0:
                    similar_indices[i].append(films.index[j])
                    similar_titles[i].append(film2['title'])
                    if verbose:
                        print('%s <- %s' % (film1['title'], film2['title']))
                elif datediff.days < 0:
                    similar_indices[j].append(films.index[i])
                    similar_titles[j].append(film1['title'])
                    if verbose:
                        print('%s <- %s' % (film2['title'], film1['title']))
    
    return (similar_indices, similar_titles)
    
def prediction_result(films, model, features, response, transform=None):
    prediction = model.predict(features)
    if transform is not None:
        prediction = transform(prediction)
    return pd.DataFrame({'title': [x[:25] for x in films['title']], 
                         'prediction': np.round(prediction, 0), 
                         'actual': np.round(response, 0), 
                         'error': np.round(response - prediction, 0)})

def r2_result(result):
    total_var = sum((result['actual'] - result['actual'].mean())**2)
    pred_var = sum((result['actual'] - result['prediction'])**2)
    return 1 - pred_var/total_var

def read_film_csv(film_csv, encoding='utf-8'):
    '''Read a saved film csv file (converts certain columns)'''
    films = pd.read_csv(film_csv, encoding=encoding)
    films['opening_date'] = [datetime.datetime.strptime(x, '%Y-%m-%d').date() for x in films['opening_date']]
    return films

def write_film_csv(films, film_csv, encoding='utf-8'):
    '''Writes a film dataframe to a csv file (converts certain columns)'''
    films.to_csv(film_csv, encoding=encoding)
    return films

def load_wikipedia_revisions(film, output_dir):
    filename = '%s.revisions' % hashlib.md5(film['wiki_title']).hexdigest()
    filename = os.path.join(output_dir, filename)
    if not os.path.isfile(filename):
        raise Exception('Error: expected file %s not found for %s' % (filename, film['wiki_title']))
    revisions = joblib.load(filename)
    for rev in revisions:
        if 'timestamp' in rev:
            rev['timestamp'] = datetime.datetime.strptime(rev['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
    return revisions

def generate_features(films, output_dir, start_year, add_const=True, verbose=False):
    
    use_films = films[films['year'] >= start_year]
    
    response = use_films['opening_gross'] / use_films['opening_theaters']
    n = len(use_films.index)
    features = { 'edit_runs_7_28': [0] * n,      # number of edits, counting consecutive edits by same user as one
                 'edit_runs_0_7': [0] * n,
                 'word_imax': [0] * n,
                 'similar_revenue': [0] * n,
                 'friday_open': [0] * n,
                 'thursday_open': [0] * n,
                 'wednesday_open': [0] * n,
               }
    
    for (i, film_i) in enumerate(use_films.index):
        
        film = films.ix[film_i]
        revisions = load_wikipedia_revisions(film, output_dir)
        if verbose:
            print '(%d) %s / %d revisions' % (film_i, film['wiki_title'], len(revisions))
            
        if film['wiki_title'] is None:
            raise Exception('Error: no wiki_title found for film %s, index %i' % (film['title'], i))
        
        # Genre indicators
        
        #genres = set(film['genres'].split(','))
        #if 'Romance' in genres:
        #    features['genre_romance'][i] = 1
        #if 'Horror' in genres:
        #    features['genre_horror'][i] = 1
        #if 'Animation' in genres and ('Kids & Family' in genres or film['mpaa_rating'] == 'G'):
        #    features['genre_family_animation'][i] = 1
        #if 'Animation' in genres and not ('Kids & Family' in genres or film['mpaa_rating'] == 'G'):
        #    features['genre_nonfamily_animation'][i] = 1
        
        # Revision-based features
        
        prev_editor = None
        edit_runs_0_7 = 0
        edit_runs_7_28 = 0
        for rev in revisions:
            if rev['user'] != prev_editor:
                daydiff = (film['opening_date'] - rev['timestamp'].date()).days
                if daydiff <= 7:
                    edit_runs_0_7 += 1
                elif daydiff <= 28:
                    edit_runs_7_28 += 1
                prev_editor = rev['user']
        features['edit_runs_0_7'][i] = edit_runs_0_7
        features['edit_runs_7_28'][i] = edit_runs_7_28
        
        word_imax = np.array([0] * len(revisions))
        imax_re = r'\Wimax'
        
        for (j, rev) in enumerate(revisions):
            if '*' in rev:
                content = rev['*'].lower()
                word_imax[j] = len(re.findall(r'imax', content))
                    
        if len(revisions) > 0:
            features['word_imax'][i] = word_imax.mean()
        
        if len(film['similar_indices']) > 0:
            similar_films = films.ix[film['similar_indices']]
            features['similar_revenue'][i] = (similar_films['opening_gross'] / similar_films['opening_theaters']).mean()
        
        weekday = film['opening_date'].weekday()
        if weekday == 2:
            features['wednesday_open'][i] = 1
        elif weekday == 3:
            features['thursday_open'][i] = 1
        elif weekday == 4:
            features['friday_open'][i] = 1
    
    features = pd.DataFrame(features, index=use_films.index)
    
    features['runtime'] = films['runtime']
    features['runtime'][features['runtime'].isnull()] = 0
    features['opening_theaters'] = films['opening_theaters']
    features['edit_runs_0_7_sequel'] = features['edit_runs_0_7'] * features['similar_revenue']
    features['edit_runs_7_28_sequel'] = features['edit_runs_7_28'] * features['similar_revenue']
    
    if add_const:
        features['const'] = 1
    return (use_films, response, features)
