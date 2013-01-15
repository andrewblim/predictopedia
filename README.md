
# Code documentation

This readme is simply intended to be a guide to rerunning the scripts and reproducing the results in `docs/writeup.pdf`, and not a detailed explanation of the analysis. For a detailed description of this project, see `docs/writeup.pdf`. 

## Dependencies

Names listed are the names of the packages in `pip`. Versions listed are what I used; other versions may work as well. I ran everything under Python 2.7.3. 

- numpy 1.6.2
- pandas 0.9.1
- beautifulsoup 4.1.3
- scikit-learn 0.12.1
- joblib 0.7.0b
- simplejson 2.6.2
- PyYAML 3.10

## Regenerating the data and model fit

To regenerate the raw data, run the script `retrieve.py`. This will generate a file `films.csv` containing a list of films to analyze and various descriptive features, and also will populate the `revisions` directory with several pickle files containing Wikipedia revision data. When run as is, the script will download about 2.2 GB of data into `revisions`. Keep in mind that this will also consume a significant fraction of a day's quota worth of Rotten Tomatoes API queries (as of this writing, the free tier is capped at 10,000 requests a day). This may take a while to run, something on the order of 1 hour on my Macbook Air, but you only need to run it once. 

Once this has been completed, run the script `fit.py`. I suggest running it from interactive Python with `execfile(fit.py)` so that you can further examine the fitted model object, the results and error, etc. as you see fit. But it will also print the prediction results to stdout, so you can run it from the command line as well and get the predictions that way. This script takes a bit of time to run, something on the order of 15 minutes. 

Be aware that numbers may not be exactly the same if the online data has changed - I observed some changes (slightly different Rotten Tomatoes data, revised revenue numbers for recent films, etc.) while working on this project. I have not included my own `films.csv` used to generate the writeup because it contains some data acquired from Rotten Tomatoes which I may not have the right to distribute. 

## Index of contents

`config/`

This directory contains YAML configuration files for the scripts in `retrieval/`. You will have to enter a Rotten Tomatoes API key into `rottentomatoes.yaml` in order to run the data scrape. Most of the configurations involve manual overrides for film titles for which the data sources' APIs did not correspond cleanly. 

`docs/`

A writeup of the motivations behind this project and an explanation of the analysis. See `docs/writeup.pdf`. 

`features.py`

This file contains functions for feature generation from the raw data. 

`films.csv`

Not present in this repository, but when you run through the first part of the procedure in the "Regenerating the data and model fit" section above, you will have generated this csv file containing a list of films and associated descriptive data. 

`fit.py`

A script that fits a gradient boosting tree model based on the data in `films.csv` and the `revisions/` directory. Outputs the result to stdout; when run from within a Python command line, the model is stored in the `model` variable. Takes some time to run. 

`images.py`

A file containing some ad hoc functions written for the purpose of generating illustrations for the writeup in `docs/`. 

`README.md`

This file, of course. 

`retrieve.py`

A script that runs all the retrieval functions at once and generates `films.csv` and revision data into the `revisions/` directory. 

`retrieval/`

This directory contains scripts to retrieve data from Box Office Mojo, Rotten Tomatoes, and Wikipedia. 

`revisions/`

This directory is empty in this repository, but is the default target for local storage Wikipedia revisions (to obviate the need to repeatedly query Wikipedia's web server when running the model again and again). It contains about 2 GB of data after the scrape has run. 
