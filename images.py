from retrieval.wikipedia import load_wikipedia_revisions
import matplotlib.pyplot as plt

def wikipedia_revision_pattern(films, revision_dir, output, verbose=False,
                               day_limit=28):
    '''
    Generates a histogram of the 
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