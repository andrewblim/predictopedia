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
    '''Read a saved film csv file (converts dates to date objects)'''
    films = pd.read_csv(film_csv, encoding=encoding)
    films['opening_date'] = [datetime.datetime.strptime(x, '%Y-%m-%d').date() for x in films['opening_date']]
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

def generate_features(films, output_dir, add_const=True, verbose=False):
    
    response = films['opening_gross'] / films['opening_theaters']
    n = len(films.index)
    features = { 'edit_runs_7_28': [0] * n,      # number of edits, counting consecutive edits by same user as one
                 'edit_runs_0_7': [0] * n,
                 'genre_romance': [0] * n,
                 'genre_horror': [0] * n,
                 'genre_family_animation': [0] * n,
                 'genre_nonfamily_animation': [0] * n,
                 'word_sequel': [0] * n,
                 'word_imax': [0] * n,
                 'word_advertising': [0] * n,
               }
    
    for (i, film_i) in enumerate(films.index):
        
        film = films.ix[film_i]
        revisions = load_wikipedia_revisions(film, output_dir)
        if verbose:
            print '(%d) %s / %d revisions' % (film_i, film['wiki_title'], len(revisions))
            
        if film['wiki_title'] is None:
            raise Exception('Error: no wiki_title found for film %s, index %i' % (film['title'], i))
        
        # Genre indicators
        
        genres = set(film['genres'].split(','))
        if 'Romance' in genres:
            features['genre_romance'][i] = 1
        if 'Horror' in genres:
            features['genre_horror'][i] = 1
        if 'Animation' in genres and ('Kids & Family' in genres or film['mpaa_rating'] == 'G'):
            features['genre_family_animation'][i] = 1
        if 'Animation' in genres and not ('Kids & Family' in genres or film['mpaa_rating'] == 'G'):
            features['genre_nonfamily_animation'][i] = 1
        
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
        
        word_sequel = np.array([0] * len(revisions))
        word_imax = np.array([0] * len(revisions))
        word_advertising = np.array([0] * len(revisions))
        sequel_re = r'\W(sequel)|(prequel)|(series)|(install?ment)|(trilogy)|(quadrilogy)'
        imax_re = r'\Wimax'
        advertising_re = r'\W(market)|(advert)|(promot)|(trailer)|(teaser)|(fans?\W)'
        
        for (j, rev) in enumerate(revisions):
            if '*' in rev:
                content = rev['*'].lower()
                word_sequel[j] = len(re.findall(sequel_re, content))
                word_imax[j] = len(re.findall(r'imax', content))
                word_advertising[j] = len(re.findall(r'advertising', content))
                    
        if len(revisions) > 0:
            features['word_sequel'][i] = word_sequel.mean()
            features['word_imax'][i] = word_imax.mean()
            features['word_advertising'][i] = word_advertising.mean()
    
    features['runtime'] = films['runtime']
    features['runtime'][features['runtime'].isnull()] = 0
    features['opening_theaters'] = films['opening_theaters']
    
    features = pd.DataFrame(features, index=films.index)
    
    if add_const:
        features['const'] = 1
    return (response, features)
