from bs4 import BeautifulSoup
import re
import simplejson as json
import urllib
import urllib2

def box_office_data(years, min_opening_theaters=None, verbose=False):
    
    if verbose:
        print('Obtaining box office gross data...')
    films = pd.DataFrame(domestic_gross(years, verbose))
    if min_opening_theaters is not None:
        min_filter = films['opening_theaters'] > min_opening_theaters
        if verbose:
            print('%d of %d entries meet min threshold of %d opening theaters' % \
                  (sum(min_filter), len(films), min_opening_theaters))
        films = films[min_filter]
    
    if verbose:
        print('Matching to Wikipedia titles...')
    wikipedia_data = []
    for i in films.index:
        if verbose:
            print('%s' % films.ix[i]['title'])
        wikipedia_data.append(retrieve_wikipedia_title(films.ix[i], verbose=verbose))
    wikipedia_attach = pd.DataFrame(wikipedia_data, index=films.index)
    for col in wikipedia_attach.columns:
        films[col] = wikipedia_attach[col]
    return films

def parse_domestic_gross_page(url, year):
    soup = BeautifulSoup(urllib2.urlopen(url))
    films = []
    table = soup.find('td', text='Rank').parent.parent
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) == 9:
            title = cells[1].get_text()
            try: total_gross = int(re.sub('\D', '', cells[3].get_text()))
            except: total_gross = None
            try: total_theaters = int(re.sub('\D', '', cells[4].get_text()))
            except: total_theaters = None
            try: opening_gross = int(re.sub('\D', '', cells[5].get_text()))
            except: opening_gross = None
            try: opening_theaters = int(re.sub('\D', '', cells[6].get_text()))
            except: opening_theaters = None
            films.append({ 'title': title, 
                           'year': year, 
                           'total_gross': total_gross, 
                           'total_theaters': total_theaters, 
                           'opening_gross': opening_gross, 
                           'opening_theaters': opening_theaters
                          })
    return films

def domestic_gross(years, verbose=False):
    films = []
    url_query = r'http://www.boxofficemojo.com/yearly/chart/'
    for year in years:
        url = r'%s?page=1&view=releasedate&view2=domestic&yr=%d&p=.htm' % (url_query, year)
        soup = BeautifulSoup(urllib2.urlopen(url))
        first_page_link = soup.find('center')
        page_count = len(first_page_link.find_all('a')) + 1
        for i in range(1, page_count+1):
            if verbose:
                print('%d page %d' % (year, i))
            url = r'%s?page=%d&view=releasedate&view2=domestic&yr=%d&p=.htm' % (url_query, i, year)
            films.extend(parse_domestic_gross_page(url, year))
    return films

def retrieve_wikipedia_title(film, limit=15, verbose=False):
    
    # Note: Wikipedia won't return more than 15 hits, so there's no point in
    # setting limit > 15. 
    
    year_film_re = re.compile(r'\(%d film\)$' % film['year'])
    film_re = re.compile(r'\(film\)$')
    api_query = r'http://en.wikipedia.org/w/api.php?format=json&action=opensearch&search=%s&limit=%d' % \
                (urllib.quote(film['title']), limit)
    query_result = json.loads(urllib2.urlopen(api_query).read())
    hits = query_result[1]
    
    # easy cases first
    
    if len(hits) == 0:
        page, arrival = None, 'no_hits'
    elif len(hits) == 1:
        page, arrival = hits[0], 'one_hit'
    else:
        
        # First try to find a year-specific match, like "Alice in 
        # Wonderland (2010 film)"
        
        year_film_matches = find_re_matches(year_film_re, hits)
        if len(year_film_matches) == 1:
            page, arrival = year_film_matches[0], 'year_film_hit'
        elif len(year_film_matches) > 1:
            page, arrival = year_film_matches[0], 'year_film_first_hit'
        
        else:
            
            # Now try for just the film label, like "Shutter Island (film)"
            
            film_matches = find_re_matches(film_re, hits)
            if len(film_matches) == 1:
                page, arrival = film_matches[0], 'film_hit'
            elif len(film_matches) > 1:
                page, arrival = film_matches[0], 'film_first_hit'
            else:
                
                # Are there a suspiciously large number of hits? If so, you may
                # have a generic title that returns lots of hits, like "The 
                # American", where "The American (2012 film)" doesn't place in 
                # the top 15. Try directly querying w/the label appended. 
                
                if len(hits) == limit:
                    api_query2 = r'http://en.wikipedia.org/w/api.php?format=json&action=opensearch&search=%s&limit=%d' % \
                                 (urllib.quote(film['title'] + (' (%d film)' % film['year'])), limit)
                    query_result2 = json.loads(urllib2.urlopen(api_query2).read())
                    hits2 = query_result2[1]
                    if len(hits2) > 0:
                        page, arrival = hits2[0], 'requery_film_hit'
                    else:
                        api_query3 = r'http://en.wikipedia.org/w/api.php?format=json&action=opensearch&search=%s&limit=%d' % \
                                     (urllib.quote(film['title'] + ' (film)'), limit)
                        query_result3 = json.loads(urllib2.urlopen(api_query3).read())
                        hits3 = query_result3[1]
                        if len(hits3) > 0:
                            page, arrival = hits3[0], 'requery2_film_hit'
                        else:
                            page, arrival = hits[0], 'first_hit'  # Just go with the first hit at this point
                
                else:
                    page, arrival = hits[0], 'first_hit'  # Just go with the first hit at this point
    
    return { 'page_title' : page, 'search_resolution' : arrival }

def find_re_matches(regexp, hits):
    matches = []
    for hit in hits:
        if regexp.search(hit) is not None:
            matches.append(hit)
    return matches