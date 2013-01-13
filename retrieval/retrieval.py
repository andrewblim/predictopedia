import boxofficemojo
import rottentomatoes
import wikipedia
import datetime
import pandas as pd

def read_film_csv(film_csv, encoding='utf-8'):
    '''Read a saved film csv file (converts certain columns)'''
    films = pd.read_csv(film_csv, encoding=encoding)
    films['opening_date'] = [datetime.datetime.strptime(x, '%Y-%m-%d').date() for x in films['opening_date']]
    return films

def write_film_csv(films, film_csv, encoding='utf-8'):
    '''Writes a film dataframe to a csv file (converts certain columns)'''
    films.to_csv(film_csv, index=False, encoding=encoding)
    return films


def retrieve_all_data(years, 
                      output_csv,
                      wikipedia_scrape_dir=None,
                      wikipedia_horizon_start=0,
                      wikipedia_horizon_end=28,
                      http_max_attempts=3,
                      boxofficemojo_config_file='config/boxofficemojo.yaml',
                      rottentomatoes_config_file='config/rottentomatoes.yaml',
                      wikipedia_config_file='config/wikipedia.yaml',
                      verbose=True):

    films = boxofficemojo.domestic_gross(years=years,
                                         config_file=boxofficemojo_config_file,
                                         http_max_attempts=http_max_attempts,
                                         verbose=verbose)
    
    films = rottentomatoes.attach_rt_data(films=films,
                                          config_file=rottentomatoes_config_file,
                                          http_max_attempts=http_max_attempts,
                                          verbose=verbose)
    
    films = wikipedia.attach_wikipedia_titles(films=films,
                                              config_file=wikipedia_config_file,
                                              http_max_attempts=http_max_attempts,
                                              verbose=verbose)
    
    write_film_csv(films, output_csv)
    
    if wikipedia_scrape_dir is not None:
        wikipedia.film_revision_scrape(films=films,
                                       output_dir=wikipedia_scrape_dir,
                                       horizon_start=wikipedia_horizon_start,
                                       horizon_end=wikipedia_horizon_end,
                                       http_max_attempts=http_max_attempts,
                                       verbose=verbose)
        
    return films