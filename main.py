''' Scrape book data from Goodreads starting from a given book URL.
    Extract title, series, contributors, and related book links.
    Save data to CSV and track scraped books to avoid duplicates.'''
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

from time import sleep

starting_point = 'https://www.goodreads.com/book/show/157993.The_Little_Prince'
harry_potter = 'https://www.goodreads.com/book/show/42844155-harry-potter-and-the-sorcerer-s-stone'
count = 0

def scrape(page, url, scraped):
    ''' Extract book data from page'''
    global count
    # Some simple logging
    print(f'{count} {url}')
    count += 1
    soup = BeautifulSoup(page, 'html.parser')
    # For debugging, save the page locally
    with open('debug.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    title_section = soup.select_one('.BookPageTitleSection')
    title = title_section.select_one('.Text__title1').get_text(strip=True)
    series = title_section.select_one('.Text__title3')
    if series is not None:
        series = series.get_text(strip=True).split('#')[0].strip()
    else:
        series = 'None'
    contributors = soup.select_one('.ContributorLinksList').select('.ContributorLink__name')
    contributors_list = [contributor.get_text(strip=True) for contributor in contributors]
    contributors_str = '; '.join(contributors_list) 
    rating_section = soup.select_one('.RatingStatistics')
    average_rating = rating_section.select_one('.RatingStatistics__rating').get_text(strip=True)
    rating_statistics_meta = rating_section.select_one('.RatingStatistics__meta').get_text(strip=True)\
        .replace('ratings', ' ').replace('reviews', '').replace('\xa0', '').split(' ')
    number_of_ratings = rating_statistics_meta[0]
    number_of_reviews = rating_statistics_meta[1]
    description = soup.select_one('.BookPageMetadataSection__description').get_text(strip=True)
    featured_details = soup.select_one('.FeaturedDetails').select('p')
    number_of_pages = 'Unknown'
    publishing_date = 'Unknown'
    if len(featured_details) >= 2:
        pages_details = featured_details[0].get_text(strip=True)
        if 'pages' in pages_details:
            number_of_pages = pages_details.split('pages')[0].strip()
        publishing_details = featured_details[1].get_text(strip=True)
        if 'ublished' in publishing_details:
            publishing_date = publishing_details.split('ublished')[1].strip()
    genres_section = soup.select_one('.BookPageMetadataSection__genres')
    if genres_section is not None:
        genres = [genre.get_text(strip=True) for genre in genres_section.select('.BookPageMetadataSection__genreButton')]
        genres_str = '; '.join(genres)
    else:
        genres_str = 'Unknown'
    
    related_soup = soup.select_one('.BookPage__relatedTopContent').select('.BookCard__clickCardTarget')
    related_books = [next.get('href') for next in related_soup]
    print(related_books, type(related_books))
    next = None
    for next in related_books:
        next = clean_url(next)
        if id(next) not in scraped:
            break
    csv_line = f'"{title}","{series}","{contributors_str}","{average_rating}","{number_of_ratings}","{number_of_reviews}","{description}","{number_of_pages}","{publishing_date}","{genres_str}","{url}"\n'
    return csv_line, next

def scroll(driver, url):
    ''' Open page and scroll to related books section to load content '''
    driver.get(url)
    related_element = driver.find_element(By.CLASS_NAME, 'BookPage__relatedTopContent')
    ActionChains(driver).scroll_to_element(related_element).perform()
    sleep(1)  # Wait for content to load
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
    print(f'Next: {url}')
    print('Scraping complete. No more new books found.')
    print('Consider starting again from a different book URL to explore more.')
    driver.quit()