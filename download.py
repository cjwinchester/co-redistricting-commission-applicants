import time
import random
import csv
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


BASE_URL = 'https://redistricting.colorado.gov'
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
URL_PATTERN = '{}/{}_applicants/'

PAGES_TO_SCRAPE = ['congressional', 'legislative']

TIMES_APPLIED_LOOKUP_FILE = 'times_applied.csv'


def gather_links(soup):
    ''' given a bs4 object, grab the table data '''
    data = []
    table = soup.find('table')
    rows = table.find_all('tr')[1:]
    for row in rows:
        cells = row.find_all('td')
        link = cells[0].a['href']
        added = cells[-1].text
        data.append({
            'link': f'{BASE_URL}{link}',
            'added': added
        })
    return data


def get_init_data(url):
    ''' get initial data from a search page:
          the first page of results and the
          number of pages to iterate through
    '''
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    p1data = gather_links(soup)
    max_pages_link = soup.find('a', string='Last »')['href']
    parsed_url = urlparse(max_pages_link)
    max_pages = int(parse_qs(parsed_url.query)['page'][0])
    return {
        'p1data': p1data,
        'max_pages': max_pages
    }


def download_pages():
    ''' cycle through both apps and download the pages
        linked to from all the search pages -- also
        creates an intermediary file to keep track of
        the times when people submitted their applications
    '''

    # open the file and write the headers
    talf_out = open(TIMES_APPLIED_LOOKUP_FILE, 'w')
    headers = ['commission_type', 'id', 'time_applied']
    writer = csv.DictWriter(talf_out, fieldnames=headers)
    writer.writeheader()

    # loop over the commission type directories
    for page in PAGES_TO_SCRAPE:

        # build the URL
        url = URL_PATTERN.format(
            BASE_URL,
            page
        )

        # fetch initial data
        init_data = get_init_data(url)
        links = init_data['p1data']
        max_pages = init_data['max_pages']

        # hol up
        time.sleep(random.uniform(1, 2))

        # loop over the range of pages
        for page_no in range(2, max_pages+1):

            # grab the next page of search results with params
            r = requests.get(url, params={'page': page_no})

            # soup the HTML and call the extraction function
            soup = BeautifulSoup(r.text, 'html.parser')
            new_links = gather_links(soup)

            # add to the running list of detail links
            links = links + new_links

            # just a sec k
            time.sleep(random.uniform(1, 2))

        # now, loop over the detail page links
        for link in links:

            # get the applicant's ID number
            applicant_id = link['link'].split('/')[-1]

            # and reformat the application date to ISO 8601
            datetime_applied = datetime.strptime(
                link['added'].replace(' UTC', ''),
                '%Y-%m-%d %H:%M:%S'
            ).isoformat() + 'Z'

            # write timestamp data to file
            writer.writerow({
                'commission_type': page,
                'id': applicant_id,
                'time_applied': datetime_applied
            })

            # make a file path to the HTML file
            filepath = os.path.join(
                THIS_DIR,
                page,
                applicant_id
            ) + '.html'

            # check if we've already downloaded this one
            if not os.path.isfile(filepath):

                # if not, grab the detail page
                detail_page = requests.get(link['link'])

                # write it to file
                with open(f'{filepath}', 'w') as outfile:
                    outfile.write(detail_page.text)

                # holler at us
                print(f'Wrote {filepath}')

                # won't take but a moment
                time.sleep(random.uniform(1, 2))

    # close the file yo
    talf_out.close()


if __name__ == '__main__':
    download_pages()
