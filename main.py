from datetime import datetime

from download import download_pages
from scrape import scrape_pages


if __name__ == '__main__':
    download_pages()
    scrape_pages()

    with open('updated', 'w') as outfile:
        outfile.write(datetime.utcnow().isoformat() + 'Z')
