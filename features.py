from bs4 import BeautifulSoup
from retrieval.wikipedia import load_wikipedia_revisions
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

def common3(members1, members2):
    common = len(members1 & members2)
    return 1 if common >= 3 else 0

def common2to4(members1, members2):
    common = len(members1 & members2)
    return max(0, min(1, (common - 1)/3.0))

def subsequence_scores(films, metric, max_days_apart=1825, verbose=False):
    
    members = {}
    scores = pd.DataFrame(index=films.index, columns=films.index)
    
    for i in films.index:
        film = films.ix[i]
        members[i] = set()
        if pd.notnull(film['directors']):
            members[i] |= set([film['directors']])  # don't split - treat directing duos as one
        if pd.notnull(film['actors']):
            members[i] |= set(film['actors'].split(','))
    
    for i in range(len(films.index)):
        
        film1 = films.ix[films.index[i]]
        for j in range(i, len(films.index)):
            
            film2 = films.ix[films.index[j]]
            members1 = members[i]
            members2 = members[j]
            
            datediff = film1['opening_date'] - film2['opening_date']
            if abs(datediff.days) > max_days_apart or datediff.days == 0:
                scores[i][j] = 0
                scores[j][i] = 0
            else: 
                score = metric(members1, members2)
                if datediff.days > 0:
                    scores[i][j] = score
                    scores[j][i] = 0
                    if verbose and score > 0:
                        print('%s <- %s (%.4f)' % (film1['title'], film2['title'], score))
                else:
                    scores[j][i] = score
                    scores[i][j] = 0
                    if verbose and score > 0:
                        print('%s <- %s (%.4f)' % (film2['title'], film1['title'], score))
    
    return scores
    
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

def generate_features(films, full_films, subsequence, output_dir, add_const=True, 
                      verbose=False):
    
    response = films['opening_gross'] / films['opening_theaters']
    n = len(films.index)
    features = { 'edit_runs_7_28': [0] * n,      # number of edits, counting consecutive edits by same user as one
                 'edit_runs_0_7': [0] * n,
                 'word_imax': [0] * n,
                 'word_jpg': [0] * n,
                 'word_headings': [0] * n,
                 'avg_size': [0] * n,
                 'similar_revenue': [0] * n,
                 'genre_action': [0] * n,
                 'genre_animation': [0] * n,
                 'genre_arthouse': [0] * n,
                 'genre_classics': [0] * n,
                 'genre_comedy': [0] * n,
                 'genre_cult': [0] * n,
                 'genre_documentary': [0] * n,
                 'genre_drama': [0] * n,
                 'genre_horror': [0] * n,
                 'genre_kids': [0] * n,
                 'genre_musical': [0] * n,
                 'genre_mystery': [0] * n,
                 'genre_romance': [0] * n,
                 'genre_scifi': [0] * n,
                 'genre_special': [0] * n,
                 'genre_sports': [0] * n,
                 'genre_tv': [0] * n,
                 'genre_western': [0] * n,
                 'mpaa_g': [0] * n,
                 'mpaa_pg': [0] * n,
                 'mpaa_pg13': [0] * n,
                 'release_friday': [0] * n,
               }
    
    for (i, film_i) in enumerate(films.index):
        
        film = films.ix[film_i]
        revisions = load_wikipedia_revisions(film, output_dir)
        if verbose:
            print '(%d) %s / %d revisions' % (film_i, film['wiki_title'], len(revisions))
            
        if film['wiki_title'] is None:
            raise Exception('Error: no wiki_title found for film %s, index %i' % (film['title'], i))
        
        # Genre indicators
        
        if not pd.isnull(film['genres']):
            genres = set(film['genres'].split(','))
            if 'Action & Adventure' in genres:
                features['genre_action'][i] = 1
            if 'Animation' in genres:
                features['genre_animation'][i] = 1
            if 'Art House & International' in genres:
                features['genre_arthouse'][i] = 1
            if 'Classics' in genres:
                features['genre_classics'][i] = 1
            if 'Comedy' in genres:
                features['genre_comedy'][i] = 1
            if 'Cult Movies' in genres:
                features['genre_cult'][i] = 1
            if 'Documentary' in genres:
                features['genre_documentary'][i] = 1
            if 'Drama' in genres:
                features['genre_drama'][i] = 1
            if 'Horror' in genres:
                features['genre_horror'][i] = 1
            if 'Kids & Family' in genres:
                features['genre_kids'][i] = 1
            if 'Musical & Performing Arts' in genres:
                features['genre_musical'][i] = 1
            if 'Mystery & Suspense' in genres:
                features['genre_mystery'][i] = 1
            if 'Romance' in genres:
                features['genre_romance'][i] = 1
            if 'Science Fiction & Fantasy' in genres:
                features['genre_scifi'][i] = 1
            if 'Special Interest' in genres:
                features['genre_special'][i] = 1
            if 'Sports & Fitness' in genres:
                features['genre_sports'][i] = 1
            if 'Television' in genres:
                features['genre_tv'][i] = 1
            if 'Western' in genres:
                features['genre_western'][i] = 1
        
        if film['mpaa_rating'] == 'G':
            features['mpaa_g'][i] = 1
        elif film['mpaa_rating'] == 'PG':
            features['mpaa_pg'][i] = 1
        elif film['mpaa_rating'] == 'PG-13':
            features['mpaa_pg13'][i] = 1
        
        # only a very few films unrated, so anything not in the above 3 buckets gets to be "R or UR"
        
        if film['opening_date'].weekday() == 5:
            features['release_friday'][i] = 1
        
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
        word_jpg = np.array([0] * len(revisions))
        word_headings = np.array([0] * len(revisions))
        sizes = np.array([0] * len(revisions))
        
        for (j, rev) in enumerate(revisions):
            if '*' in rev:
                content = rev['*'].lower()
                word_imax[j] = len(re.findall(r'\Wimax', content))
                word_jpg[j] = len(re.findall(r'File:.*\.jpe?g\|', content))
                word_headings[j] = len(re.findall(r'==.*==', content))
            sizes[j] = rev['size']
                    
        if len(revisions) > 0:
            features['word_imax'][i] = word_imax.mean()
            features['word_jpg'][i] = word_jpg.mean()
            features['word_headings'][i] = word_headings.mean()
        features['avg_size'][i] = sizes.mean()
        
        # Similar-film revenue
        
        if sum(subsequence[film_i]) > 0:
            features['similar_revenue'][i] = sum(subsequence[film_i] * full_films['opening_gross'] / \
                                                 full_films['opening_theaters']) / \
                                             float(sum(subsequence[film_i]))
        
    features = pd.DataFrame(features, index=films.index)
    
    features['runtime'] = films['runtime']
    features['runtime'][features['runtime'].isnull()] = 0
    features['opening_theaters'] = films['opening_theaters']
    features['year'] = films['year']
    
    # cross terms
    """
    features['edit07_genre_action'] = features['genre_action'] * features['edit_runs_0_7']
    features['edit07_genre_animation'] = features['genre_animation'] * features['edit_runs_0_7']
    features['edit07_genre_arthouse'] = features['genre_arthouse'] * features['edit_runs_0_7']
    features['edit07_genre_classics'] = features['genre_classics'] * features['edit_runs_0_7']
    features['edit07_genre_comedy'] = features['genre_comedy'] * features['edit_runs_0_7']
    features['edit07_genre_cult'] = features['genre_cult'] * features['edit_runs_0_7']
    features['edit07_genre_documentary'] = features['genre_documentary'] * features['edit_runs_0_7']
    features['edit07_genre_drama'] = features['genre_drama'] * features['edit_runs_0_7']
    features['edit07_genre_horror'] = features['genre_horror'] * features['edit_runs_0_7']
    features['edit07_genre_kids'] = features['genre_kids'] * features['edit_runs_0_7']
    features['edit07_genre_musical'] = features['genre_musical'] * features['edit_runs_0_7']
    features['edit07_genre_mystery'] = features['genre_mystery'] * features['edit_runs_0_7']
    features['edit07_genre_romance'] = features['genre_romance'] * features['edit_runs_0_7']
    features['edit07_genre_scifi'] = features['genre_scifi'] * features['edit_runs_0_7']
    features['edit07_genre_special'] = features['genre_special'] * features['edit_runs_0_7']
    features['edit07_genre_sports'] = features['genre_sports'] * features['edit_runs_0_7']
    features['edit07_genre_tv'] = features['genre_tv'] * features['edit_runs_0_7']
    features['edit07_genre_western'] = features['genre_western'] * features['edit_runs_0_7']
    
    features['edit728_genre_action'] = features['genre_action'] * features['edit_runs_7_28']
    features['edit728_genre_animation'] = features['genre_animation'] * features['edit_runs_7_28']
    features['edit728_genre_arthouse'] = features['genre_arthouse'] * features['edit_runs_7_28']
    features['edit728_genre_classics'] = features['genre_classics'] * features['edit_runs_7_28']
    features['edit728_genre_comedy'] = features['genre_comedy'] * features['edit_runs_7_28']
    features['edit728_genre_cult'] = features['genre_cult'] * features['edit_runs_7_28']
    features['edit728_genre_documentary'] = features['genre_documentary'] * features['edit_runs_7_28']
    features['edit728_genre_drama'] = features['genre_drama'] * features['edit_runs_7_28']
    features['edit728_genre_horror'] = features['genre_horror'] * features['edit_runs_7_28']
    features['edit728_genre_kids'] = features['genre_kids'] * features['edit_runs_7_28']
    features['edit728_genre_musical'] = features['genre_musical'] * features['edit_runs_7_28']
    features['edit728_genre_mystery'] = features['genre_mystery'] * features['edit_runs_7_28']
    features['edit728_genre_romance'] = features['genre_romance'] * features['edit_runs_7_28']
    features['edit728_genre_scifi'] = features['genre_scifi'] * features['edit_runs_7_28']
    features['edit728_genre_special'] = features['genre_special'] * features['edit_runs_7_28']
    features['edit728_genre_sports'] = features['genre_sports'] * features['edit_runs_7_28']
    features['edit728_genre_tv'] = features['genre_tv'] * features['edit_runs_7_28']
    features['edit728_genre_western'] = features['genre_western'] * features['edit_runs_7_28']
    
    features['edit_07_mpaa_g'] = features['mpaa_g'] * features['edit_runs_0_7']
    features['edit_07_mpaa_pg'] = features['mpaa_pg'] * features['edit_runs_0_7']
    features['edit_07_mpaa_pg13'] = features['mpaa_pg13'] * features['edit_runs_0_7']
    features['edit_728_mpaa_g'] = features['mpaa_g'] * features['edit_runs_7_28']
    features['edit_728_mpaa_pg'] = features['mpaa_pg'] * features['edit_runs_7_28']
    features['edit_728_mpaa_pg13'] = features['mpaa_pg13'] * features['edit_runs_7_28']
    
    features['edit_07_release_friday'] = features['release_friday'] * features['edit_runs_0_7']
    features['edit_728_release_friday'] = features['release_friday'] * features['edit_runs_7_28']
    """
    if add_const:
        features['const'] = 1
    return (features, response)
