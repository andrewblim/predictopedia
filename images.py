from retrieval.wikipedia import load_wikipedia_revisions
from sklearn import ensemble
from sklearn.cross_validation import cross_val_score
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# These are ad-hoc functions intended to produce the graphs in the writeup. 
# They are not directly part of the script functionality. 

def wikipedia_revision_pattern(films, revision_dir, output, verbose=False,
                               day_limit=28):
    '''
    Generates a histogram of the Wikipedia article edit frequency in the days
    prior to films' release dates. 
    '''
    days_back = []
    for i in films.index:
        film = films.ix[i]
        if verbose:
            print(film['title'])
        revisions = load_wikipedia_revisions(film, revision_dir)
        for rev in revisions:
            days_back.append((film['opening_date'] - rev['timestamp'].date()).days)
    plt.figure(figsize=(5,2.5))
    ax = plt.axes()
    ax.hist(days_back, bins=day_limit)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')
    ax.set_xlim(left=1, right=day_limit)
    plt.savefig(output, facecolor='white')
    plt.close()

def gradient_boost_parameter_grid(train_features, train_response, 
                                  test_features, test_response, 
                                  max_depths=pd.Series([2,3,5,7,10]),
                                  n_estimators=np.arange(10,301,10),
                                  cv_folds=5,
                                  verbose=False, **kwargs):
    
    train_r2s = {}
    test_r2s = {}
    
    for max_depth in max_depths:
        train_r2s[max_depth] = {}
        test_r2s[max_depth] = {}
        for n in n_estimators:
            if verbose:
                print('Max depth = %d, estimators = %d' % (max_depth, n))
            model = ensemble.GradientBoostingRegressor(n_estimators=n, max_depth=max_depth, **kwargs)
            model.fit(train_features, train_response)
            train_r2 = cross_val_score(model, train_features, train_response, cv=cv_folds).mean()
            test_r2 = 1 - sum((test_response - model.predict(test_features))**2) / \
                      float(sum((test_response - test_response.mean())**2))
            train_r2s[max_depth][n] = train_r2
            test_r2s[max_depth][n] = test_r2
    
    return (pd.DataFrame(train_r2s), pd.DataFrame(test_r2s))

def gradient_boost_parameter_graph(grid, output):
    
    plt.figure(figsize=(4,3.5))
    plt.xlabel('# of estimators', fontsize='x-small')
    plt.ylabel('R^2', fontsize='x-small')
    ax = plt.axes()
    for col in grid.columns:
        ax.plot(grid.index, grid[col])
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')
    plt.legend(tuple(['%d leaves' % x for x in grid.columns]), 
               loc='lower right', prop={'size': 'x-small'})
    plt.savefig(output, facecolor='white')
    plt.close()

def scatter_result(result, output):
    
    plt.figure(figsize=(3.25,3.25))
    plt.xlabel('Actual revenue theater (thousands $)', fontsize='x-small')
    plt.ylabel('Predicted revenue/theater (thousands $)', fontsize='x-small')
    ax = plt.axes()
    ax.scatter(result['actual']/1000.0, result['prediction']/1000.0)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize('x-small')
    plt.savefig(output, facecolor='white')
    plt.close()