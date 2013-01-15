from sklearn import ensemble
import features
import numpy as np
import retrieval

if __name__ == '__main__':
    
    films = retrieval.read_film_csv('films.csv')
    train_films = films[np.logical_and(films['year'] >= 2007, films['year'] <= 2011)]
    test_films = films[films['year'] == 2012]
    
    data = features.train_and_test_data(train_films, test_films, 'revisions', verbose=True)
    (base_train_features, train_response, base_test_features, test_response) = data
    
    subseq = features.subsequence_scores(films, features.people_by_genres_jaccard, verbose=True)
    train_features = features.attach_similar_revenue(films, base_train_features, subseq)
    test_features = features.attach_similar_revenue(films, base_test_features, subseq)
    train_features_nowiki = train_features.copy()
    test_features_nowiki = test_features.copy()
    
    del train_features_nowiki['avg_size']
    del train_features_nowiki['edit_runs_0_7']
    del train_features_nowiki['edit_runs_7_28']
    del train_features_nowiki['word_extfile']
    del train_features_nowiki['word_headings']
    del train_features_nowiki['word_imax']
    del test_features_nowiki['avg_size']
    del test_features_nowiki['edit_runs_0_7']
    del test_features_nowiki['edit_runs_7_28']
    del test_features_nowiki['word_extfile']
    del test_features_nowiki['word_headings']
    del test_features_nowiki['word_imax']
    
    model = ensemble.GradientBoostingRegressor(n_estimators=100, max_depth=2)
    model = model.fit(train_features, train_response)
    result = features.prediction_result(test_films, model, test_features, test_response)
    
    model_nowiki = ensemble.GradientBoostingRegressor(n_estimators=100, max_depth=2)
    model_nowiki = model_nowiki.fit(train_features_nowiki, train_response)
    result_nowiki = features.prediction_result(test_films, model_nowiki, test_features_nowiki, test_response)
    
    print('With Wikipedia:')
    print(result)
    
    print('Without Wikipedia:')
    print(result_nowiki)