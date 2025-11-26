''' Scrape book data from Goodreads starting from a given book URL.
    Extract title, series, contributors, and related book links.
    Save data to CSV and track scraped books to avoid duplicates.'''
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

from time import sleep

starting_point = 'https://www.goodreads.com/book/show/10959.Sophie_s_World'
harry_potter = 'https://www.goodreads.com/book/show/42844155-harry-potter-and-the-sorcerer-s-stone'

def scrape(page, url, scraped):
    ''' Extract book data from page'''
    soup = BeautifulSoup(page, 'html.parser')
    title_section = soup.select_one('.BookPageTitleSection')
    title = title_section.select_one('.Text__title1').get_text(strip=True)
    series = title_section.select_one('.Text__title3')
    if series is not None:
        series = series.get_text(strip=True).split('#')[0]
    else:
        series = 'None'
    contributors = soup.select_one('.ContributorLinksList').select('.ContributorLink__name')
    contributors_list = [contributor.get_text(strip=True) for contributor in contributors]
    contributors_str = '; '.join(contributors_list)
    related_section = soup.select_one('.BookPage__relatedTopContent')
    related_books = [next.get('href') for next in related_section.select('a')]
    for next in related_books:
        next = clean_url(next)
        if id(next) not in scraped:
            break
        else:
            next = None
    csv_line = f'"{title}","{series}","{contributors_str}","{url}"\n'
    return csv_line, next

def scroll(driver, url):
    ''' Open page and scroll to related books section to load content '''
    driver.get(url)
    related_element = driver.find_element(By.CLASS_NAME, 'BookPage__relatedTopContent')
    ActionChains(driver).scroll_to_element(related_element).perform()
    sleep(1)  # wait for content to load
    page = driver.page_source
    return page

def clean_url(url):
    ''' Get rid of query parameters '''
    return url.split('?')[0]

def id(url):
    ''' Get unique id from url '''
    return url.split('/')[-1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help='Starting URL for scraping', default=starting_point)
    args = parser.parse_args()
    url = args.url
    driver = webdriver.Chrome()
    count = 0
    # Build set of already scraped book ids
    scraped = set()
    try:
        with open('scraped.txt', 'r', encoding='utf-8') as f:
            for line in f:
                scraped.add(line.strip())
    except FileNotFoundError:
        pass
    # Start scraping loop
    while url is not None:
        url = clean_url(url)
        page = scroll(driver, url)
        data, next = scrape(page, url, scraped)
        # Log data to csv
        with open('data.csv', 'a', encoding='utf-8') as f:
            f.write(data)
        # Log book id to scraped file
        with open('scraped.txt', 'a', encoding='utf-8') as f:
            f.write(id(url) + '\n')
        scraped.add(id(url))
        url = next
        if count == 10:
            break
        count += 1
    driver.quit()