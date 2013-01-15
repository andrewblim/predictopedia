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

### Similarity-related functions - pass these into the metric argument
### of subsequence_scores()

def jaccard_people(members1, members2):
    common = len(members1['people'] & members2['people'])
    combined = float(len(members1['people'] | members2['people']))
    if combined == 0: return 0
    return common / combined

def jaccard_genres(members1, members2):
    common = len(members1['genres'] & members2['genres'])
    combined = float(len(members1['genres'] | members2['genres']))
    if combined == 0: return 0
    return common / combined

def sorensen_people(members1, members2):
    common = len(members1['people'] & members2['people'])
    denom = float(len(members1['people']) + len(members2['people']))
    if denom == 0: return 0
    return 2 * common / denom

def sorensen_genres(members1, members2):
    common = len(members1['genres'] & members2['genres'])
    denom = float(len(members1['genres']) + len(members2['genres']))
    if denom == 0: return 0
    return 2 * common / denom

def people_by_genres_jaccard(members1, members2):
    return (jaccard_people(members1, members2) * jaccard_genres(members1, members2)) ** 0.5

def people_by_genres_sorensen(members1, members2):
    return (sorensen_people(members1, members2) * sorensen_genres(members1, members2)) ** 0.5

def subsequence_scores(films, metric, max_days_apart=1825, verbose=False):
    
    '''
    Calculates subsequence scores (similarity scores, but one-way; films have 0
    subsequence with films that were released after they were) for the films in
    the films dataframe. Returns a square matrix dataframe of subsequence 
    scores. Feature calculation for film i should use the films whose rows in
    column i have with nonzero scores. 
    '''
    
    if verbose:
        print('Calculating one=way similarities...')
    # film in column i receives films in rows j as an input
    scores = pd.DataFrame(index=films.index, columns=films.index)
    
    members = {}
    for i in films.index:
        film = films.ix[i]
        members[i] = { 'people': set(), 'genres': set() }
        if pd.notnull(film['directors']):
            members[i]['people'] |= set([film['directors']])  # don't split - treat directing duos as one
        if pd.notnull(film['actors']):
            members[i]['people'] |= set(film['actors'].split(','))
        if pd.notnull(film['genres']):
            members[i]['genres'] |= set(film['genres'].split(','))
    
    for i in range(len(films.index)):
        
        film1 = films.ix[films.index[i]]
        if verbose:
            print(film1['title'])
        
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
                else:
                    scores[j][i] = score
                    scores[i][j] = 0
    
    return scores

def print_similar_past(films, film_index, scores):
    '''Small utility function to print a film's antecedents'''
    for j in films.index:
        if scores[film_index][j] > 0:
            print('%30s <- %30s (%.4f)' % (films.ix[film_index]['title'][:30], 
                                           films.ix[j]['title'][:30], 
                                           scores[film_index][j]))

### Feature generation

def generate_features(films, output_dir, add_const=False, verbose=False):
    
    '''
    For data in films, calculates all 
    '''
    
    response = films['opening_gross'] / films['opening_theaters']
    n = len(films.index)
    features = { 'edit_runs_7_28': [0] * n, 
                 'edit_runs_0_7': [0] * n,
                 'word_imax': [0] * n,
                 'word_extfile': [0] * n,
                 'word_headings': [0] * n,
                 'avg_size': [0] * n,
                 'similar_past_revenue': [0] * n,
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
        
        # only a very few films unrated, so anything not in the above 3 buckets gets to be "R or UR"
        
        if film['mpaa_rating'] == 'G':
            features['mpaa_g'][i] = 1
        elif film['mpaa_rating'] == 'PG':
            features['mpaa_pg'][i] = 1
        elif film['mpaa_rating'] == 'PG-13':
            features['mpaa_pg13'][i] = 1
        
        if film['opening_date'].weekday() == 5:
            features['release_friday'][i] = 1
        
        # Revision-based features
        
        prev_editor = None
        edit_runs_0_7 = 0    # edit run = one string of consecutive edits by
        edit_runs_7_28 = 0   # the same author
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
        word_extfile = np.array([0] * len(revisions))
        word_headings = np.array([0] * len(revisions))
        sizes = np.array([0] * len(revisions))
        
        for (j, rev) in enumerate(revisions):
            if '*' in rev:
                content = rev['*'].lower()
                word_imax[j] = len(re.findall(r'\Wimax', content))
                word_extfile[j] = len(re.findall(r'File:.*|', content))
                word_headings[j] = len(re.findall(r'==.*==', content))
            sizes[j] = rev['size']
                    
        if len(revisions) > 0:
            features['word_imax'][i] = word_imax.mean()
            features['word_extfile'][i] = word_extfile.mean()
            features['word_headings'][i] = word_headings.mean()
        features['avg_size'][i] = sizes.mean()
        
    features = pd.DataFrame(features, index=films.index)
    
    features['runtime'] = films['runtime']
    features['runtime'][features['runtime'].isnull()] = 0
    # features['opening_theaters'] = films['opening_theaters']
    features['year'] = films['year']
    
    return (features, response)

def attach_similar_revenue(films, features, subsequence):
    '''
    Attaches similar revenues to features (based on the subsequence scores in
    subsequence) and returns it. Separated from the rest of the feature generation 
    to make it easy to try out different similarity metrics without recalculating 
    all the other features. 
    '''
    
    similar_past_revenue = [0] * len(features)
    for (i, film_i) in enumerate(features.index):
        
        # Similar-film revenue
        
        if sum(subsequence[film_i]) > 0:
            contrib = subsequence[film_i] * films['opening_gross'] / films['opening_theaters']
            similar_past_revenue[i] = sum(contrib) / float(sum(subsequence[film_i]))

    expanded_features = features.copy(deep=True)
    expanded_features['similar_past_revenue'] = similar_past_revenue
    return expanded_features

def train_and_test_data(train_films, test_films, output_dir, 
                        add_const=True, verbose=False):
    
    '''Generates test and train features and response based on the raw data.'''
    
    if verbose:
        print('Generating train features...')                        
    (train_features, train_response) = generate_features(train_films, 
                                                         output_dir,
                                                         add_const=add_const,
                                                         verbose=verbose)
    
    if verbose:
        print('Generating test features...')   
    (test_features, test_response) = generate_features(test_films, 
                                                       output_dir,
                                                       add_const=add_const,
                                                       verbose=verbose)
    
    return (train_features, train_response, test_features, test_response)

### Prediction generation

def prediction_result(films, model, features, response, transform=None):
    '''
    Returns a dataframe containing titles (abbreviated for easy display), 
    predictions, actual values, and absolute error. 
    '''
    prediction = model.predict(features)
    if transform is not None:
        prediction = transform(prediction)
    return pd.DataFrame({'title': [x for x in films['title']], 
                         'prediction': np.round(prediction, 0), 
                         'actual': np.round(response, 0), 
                         'error': np.round(response - prediction, 0)})

def r2_result(result):
    '''
    Returns the R2 of a result dataframe as returned by prediction_result. 
    '''
    total_var = sum((result['actual'] - result['actual'].mean())**2)
    pred_var = sum((result['actual'] - result['prediction'])**2)
    return 1 - pred_var/total_var