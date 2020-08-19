# Colorado redistricting commission applications
Colorado is taking applications for two citizen redistricting commissions -- one for legislative boundaries and one for congressional boundaries.

[The applicant data lives in this app](https://redistricting.colorado.gov/). This Python project scrapes the data into a single CSV, `['co-redistricting-commission-applicants.csv'`](https://github.com/cjwinchester/co-redistricting-commission-applicants/blob/master/co-redistricting-commission-applicants.csv).

### Running the script
I'm using pipenv to manage the dependencies -- `requests` and `bs4` -- but however you install them, the next step is to run `main.py`, which calls functions from `download.py` (download the individual applicant pages into the `congressional` and `legislative` directories) and `scrape.py` (parse the data into a CSV).

(The scripts also create an intermediary file, `times_applied.csv`, that is .gitignored in this repo.)