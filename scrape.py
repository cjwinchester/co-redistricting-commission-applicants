import os
import re
import csv

from download import (TIMES_APPLIED_LOOKUP_FILE,
                      PAGES_TO_SCRAPE,
                      BASE_URL,
                      URL_PATTERN)

from bs4 import BeautifulSoup


CSV_FILE_OUT = 'co-redistricting-commission-applicants.csv'

CSV_HEADERS = [
    'commission_type',
    'applicant_id',
    'application_datetime',
    'full_name',
    'other_names',
    'party_affiliation',
    'gender',
    'gender_category',
    'race',
    'latinx',
    'zip',
    'occupation',
    'education',
    'statement',
    'professional_background',
    'org_list',
    'analytic_skills',
    'consensus_statement',
    'past_political_activity',
    'application_url',
    'link_to_html'
]


detail_page_template = 'https://github.com/cjwinchester/co-redistricting-commission-applicants/blob/master/{}'  # noqa


# a lookup table to categorize the freeform text gender values
GENDER_LOOKUP = {
    'male.': 'm',
    'Female': 'f',
    'Male': 'm',
    'Cisgender male': 'm',
    'female': 'f',
    'male': 'm',
    'I am a male.': 'm',
    'Male, although I feel like it should be "identify as" instead of "identify with".': 'm',  # noqa
    'male, unless my wife says otherwise': 'm',
    'woman / female': 'f',
    'MALE': 'm',
    "I'm a man.": 'm',
    "I'm a man...this is a strange question and should have no bearing on this position": 'm',  # noqa
    'Humanity': None,
    'heterosexual male': 'm',
    'woman': 'f',
    'Heterosexual Male': 'm',
    'Male Heterosexual': 'm',
    'FEMALE': 'f',
    'man': 'm',
    'He/Him/His': 'm',
    'Transgender': 'o',
    'Woman': 'f',
    'Male.   I am also openly gay.': 'm',
    'I find this irrelevant. This is a committee to develop Legislative Districts.': None,  # noqa
    'Male.  I am also openly gay.': 'm',
    'I am an American male with military service': 'm',
    'Femaile': 'f',
    'Cisgender Male': 'm',
    'Make': 'm',  # assume typo here
    'emal': 'm',  # assume typo here
    'gay woman': 'f',
    'WOMEN': 'f',
    'gay woman': 'f',
    'Female.': 'f',
    'I identify as female and since you did not ask it anywhere, also as queer. Which is an important diversity issue in Colorado.': 'f',  # noqa
    'M': 'm',
    'female, cis-gender': 'f',
    'I’m a female by birth I identify as a woman. God created me a woman 👩': 'f',  # noqa
    'Male (He/Him)': 'm',
    'Biological Male not altered': 'm',
    'female.': 'f',
    'Hetero Female': 'f',
    'femail': 'f',
    'she/her/hers': 'f',
    'Female-also, attachments won’t upload': 'f',
    'Cis-Male/Masculine.': 'm',
    'Man': 'm',
    'cismale': 'm',
    'Cisfemale': 'f',
    'Decline': None,
    'Female. Please note that I have lived in predominantly hispanic neighborhoods for extended periods throughout my life in Colorado.': 'f',  # noqa
    'Gay Male': 'm',
    'Non-binary, genderfluid': 'o',
    'Cisgender, Gay Male': 'm',
    'Women': 'f',
    'Male (he/his - pronouns)': 'm',
    'female, cis-gender': 'f',
    'Female - hetero': 'f',
    'Cisgender, Gay Man': 'm',
    'Male.': 'm',
    'cismale': 'm',
    'I am a man.': 'm',
    'Queer woman': 'f',
    'Female. And I am queer, which you did not ask but I feel is important in the sphere of getting voices heard.': 'f',  # noqa
    'She/her/hers': 'f',
    'Male (He/Him)': 'm',
    'F': 'f',
    'Male by birth': 'm',
    'Female cisgendered': 'f',
    'ciswoman': 'f',
    'Male, I have that chromosome': 'm',
    'Female and my pronouns are she/her/hers': 'f',
    'Male, Gay': 'm',
    'He/His': 'm',
    'female/feminine': 'f',
    'Female and gender non-conforming': 'o',
    'Cis Male': 'm',
    'Female (she, her, hers pronouns)': 'f',
    'Female - She/Her/Hers': 'f',
    'Woman/female': 'f',
    'human female genome': 'f',
    'Woman/Female': 'f',
    'Female (She/Her/Hers)': 'f',
    'ciswoman': 'f',
    'woman/female': 'f',
    'Female and my pronouns are she/her/hers': 'f',
    'Female, she/her': 'f',
    'Male by birth': 'm',
    'Transgender Female': 'o',
    'Female (pronouns she her hers)': 'f',
    'female and gender non-conforming': 'o'
}

# almost every piece of data follows the same extraction process,
# with the only difference being the text (or regex) search pattern
# and the type of headline, so this here dict just
# maps the headers to the bs4 extraction rules we'll use later
SAME_FORMAT_HEDS = {
    'full_name': ('h5', re.compile('(?i)full name')),
    'party_affiliation': ('h5', re.compile('(?i)party affiliation')),
    'gender': ('h6', re.compile('(?i)gender')),
    'race': ('h6', re.compile('(?i)racial categories')),
    'zip': ('h5', re.compile('(?i)zip code')),
    'occupation': ('h5', re.compile('(?i)occupation')),
    'education': ('h5', re.compile('(?i)educational background')),
    'statement': ('h5', 'Statement'),
    'professional_background': ('h5', re.compile('(?i)professional background')),  # noqa
    'org_list': ('h5', re.compile('(?i)political and civic organizations')),
    'analytic_skills': ('h5', re.compile('(?i)analytic skills')),
    'consensus_statement': ('h5', re.compile('(?i)working with consensus')),
    'past_political_activity': ('h5', re.compile('(?i)past political activity'))  # noqa
}


def scrape_detail_page(filepath):
    ''' given a file path, open it and scrape that data! '''

    # empty dict that we'll populate as we scrape
    data_out = {}

    # open the file and read in the HTML
    with open(filepath, 'r') as infile:
        html = infile.read()

    # turn the HTML into soup
    soup = BeautifulSoup(html, 'html.parser')

    # loop over the headers
    for header in CSV_HEADERS:

        # if it's one of the values we can extract using a common
        # pattern, do that
        if header in SAME_FORMAT_HEDS.keys():

            # grab the rules -- element to search is first [0]
            # in the tuple, the text pattern is second [1]
            rec = SAME_FORMAT_HEDS[header]
            tag = soup.find(
                rec[0],
                text=rec[1]
            )

            # if we hit, grab the next thing's text and strip whitespace
            if tag:
                tag = tag.next_sibling.next_sibling.text.strip()

            # add it to the data dict
            data_out[header] = tag
        elif header == 'other_names':

            # this one was different enough to write a
            # custom condition for
            other_names = soup.find(
                'h5',
                text=re.compile('(?i)other names')
            )
            if other_names:
                other_names = other_names.next_sibling.text.strip()
            data_out[header] = other_names
        elif header == 'latinx':
            # and this one
            latinx = soup.find('h6', text=re.compile('(?i)hispanic/latino/spanish'))  # noqa
            if latinx:
                data_out[header] = True
            else:
                data_out[header] = False

    return data_out


def scrape_pages():

    # open the file with the records of when people applied
    # and make a lookup dict
    with open(TIMES_APPLIED_LOOKUP_FILE, 'r') as infile:
        reader = csv.DictReader(infile)
        lookup = {}
        for row in reader:
            lookup[row['id']] = {
                'commission_type': row['commission_type'],
                'time_applied': row['time_applied']
            }

    # open the CSV file write to
    with open(CSV_FILE_OUT, 'w') as outfile:

        # write the headers
        writer = csv.DictWriter(outfile, fieldnames=CSV_HEADERS)
        writer.writeheader()

        # loop over the page directories
        for page in PAGES_TO_SCRAPE:
            # get a list of relative links to each HTML file to scrape
            html_files = [os.path.join(page, x) for x in
                          os.listdir(page) if x.endswith('.html')]

            # loop over this list of files
            for file in html_files:

                link_to_html = detail_page_template.format(file)

                # nab the applicant ID from the filename
                applicant_id = file.split('/')[-1].split('.')[0]

                # scrape the data out of the page
                data = scrape_detail_page(file)

                # add link to html on github
                data['link_to_html'] = link_to_html

                # add the commission type and applicant ID values
                data['commission_type'] = page
                data['applicant_id'] = applicant_id

                # and the application datetime and URL to their
                # detail page
                time_applied = None
                lookup_rec = lookup.get(applicant_id, None)
                if lookup_rec:
                    time_applied = lookup_rec.get('time_applied', None)
                data['application_datetime'] = time_applied
                data['application_url'] = URL_PATTERN.format(
                    BASE_URL,
                    page
                ) + applicant_id

                # look up their gender category and add a new value
                gender_cat = GENDER_LOOKUP.get(data['gender'], None)
                data['gender_category'] = gender_cat

                # holler if we need to add a new value to the lookup dict
                if data['gender'] and data['gender'] not in GENDER_LOOKUP.keys():  # noqa
                    print('-' * 40)
                    print(data['gender'])

                # write data to file
                writer.writerow(data)


if __name__ == '__main__':
    scrape_pages()
