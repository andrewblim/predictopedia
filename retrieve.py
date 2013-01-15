import retrieval

if __name__ == '__main__':
    retrieval.retrieve_all_data(range(2002, 2013),
                                'films.csv',
                                wikipedia_scrape_dir='revisions',
                                verbose=True)