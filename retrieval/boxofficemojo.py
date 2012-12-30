from bs4 import BeautifulSoup
import datetime
import numpy as np
import pandas as pd
import re
import urllib2
import yaml

def domestic_gross(years, config_file=None, verbose=False):
    '''
    Given a year or a list of years, returns a list of dictionaries containing 
    film data for those years. 
    '''
    if verbose:
        print('Processing Box Office Mojo annual gross lists...')
    if not hasattr(years, '__iter__'):
        years = [years]
    
    if config_file is not None:
        config = yaml.load(open(config_file, 'r').read())
    else:
        config = {}
    
    films = []
    url_query = r'http://www.boxofficemojo.com/yearly/chart/'
    for year in years:
        url = r'%s?page=1&view=releasedate&view2=domestic&yr=%d&p=.htm' % (url_query, year)
        soup = BeautifulSoup(urllib2.urlopen(url))
        first_page_link = soup.find('center')
        page_count = len(first_page_link.find_all('a')) + 1
        for i in range(1, page_count+1):
            if verbose:
                print('BOM: %d page %d' % (year, i))
            url = r'%s?page=%d&view=releasedate&view2=domestic&yr=%d&p=.htm' % (url_query, i, year)
            films.extend(parse_domestic_gross_page(url, year))
    
    films = pd.DataFrame(films)
    if 'min_opening_theaters' in config:
        min_opening_theaters = int(config['min_opening_theaters'])
        films = films[films['opening_theaters'] >= min_opening_theaters]
    if 'skip_titles' in config:
        films = films[np.logical_not(films['title'].isin(config['skip_titles']))]
    if 'title_changes' in config:
        modify_index = films['title'].isin(config['title_changes'])
        films['title'][modify_index] = films['title'][modify_index].map(config['title_changes'])
    
    return films

def parse_domestic_gross_page(url, year=None):
    '''
    Parses one of Box Office Mojo's domestic gross by year lists and returns a
    pandas dataframe containing film data. 
    '''
    
    if year is None:
        try:
            year = int(re.search('yr=(\d+)', url).group(1))
        except:
            raise Exception('Unable to parse year from url %s' % url)
    
    soup = BeautifulSoup(urllib2.urlopen(url))
    films = []
    table = soup.find('td', text='Rank').parent.parent
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) == 9:
            title = cells[1].get_text()
            title = re.sub('\s+\(%d\)$' % year, '', cells[1].get_text())
            try:
                (opening_month, opening_day) = re.split('/', cells[7].get_text())
                opening_date = datetime.date(year, int(opening_month), int(opening_day))
            except:
                opening_date = None
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
                           'opening_date': opening_date,
                           'total_gross': total_gross, 
                           'total_theaters': total_theaters, 
                           'opening_gross': opening_gross, 
                           'opening_theaters': opening_theaters
                          })
    return films