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
goodreads_list = 'https://www.goodreads.com/list/show/1.Best_Books_Ever'
count = 0

def crawl(soup, scraped):
    ''' Find next related book that hasn't been scraped yet '''
    related_soup = soup.select_one('.BookPage__relatedTopContent').select('.BookCard__clickCardTarget')
    related_books = [next.get('href') for next in related_soup]
    for next in related_books:
        next = clean_url(next)
        if id(next) not in scraped:
            return next
    return None

def scrape(page, url, scraped, crawling):
    ''' Extract book data from page'''
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
    work_details_soup = soup.select_one('.WorkDetails')
    setting = 'Unknown'
    characters = 'Unknown'
    if work_details_soup is not None:
        work_details_list = work_details_soup.select('.DescListItem')
        for detail in work_details_list:
            detail_text = detail.get_text(strip=True)
            if 'Setting' in detail_text:
                setting = detail_text.split('Setting')[1].strip()
            if 'Characters' in detail_text:
                characters = detail_text.split('Characters')[1].strip()
    # Get next page
    next = None
    if crawling:
        next = crawl(soup, scraped)
    csv_line = f'"{title}"\t"{series}"\t"{contributors_str}"\t"{average_rating}"\t"{number_of_ratings}"\t"{number_of_reviews}"\t"{description}"\t"{number_of_pages}"\t"{publishing_date}"\t"{genres_str}"\t"{setting}"\t"{characters}"\t"{url}"\n'
    return csv_line, next


def get_page(driver, url):
    ''' Open page and scroll to related books section to load content '''
    driver.get(url)
    sleep(1)  # Wait for overlay to appear
    try:
        overlay_element = driver.find_element(By.CLASS_NAME, 'Overlay')
        if overlay_element is not None:
            overlay_button_element = overlay_element.find_element(By.CLASS_NAME, 'Button')
            overlay_button_element.click()
    except:
        pass
    # Click "Show more" button to expand book details
    details_button_element = driver.find_element(By.CLASS_NAME, 'BookDetails').find_element(By.CLASS_NAME, 'Button')
    with open('debug_before_click.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    details_button_element.click()
    # Scroll to related books section to load content
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
    parser.add_argument('--book', type=str, help='If set, start from book URL')
    parser.add_argument('--index', type=str, help='If set, start from index URL')
    parser.add_argument('--crawl', help='If set, crawl related books', default=False, action='store_true')
    args = parser.parse_args()
    book = args.book
    index = args.index
    crawling = args.crawl
    if book is None and index is None:
        print('Please provide either a starting book URL or an index URL.')
        exit(1)
    driver = webdriver.Chrome()
    # Build set of already scraped book ids
    scraped = set()
    try:
        with open('scraped.txt', 'r', encoding='utf-8') as f:
            for line in f:
                scraped.add(line.strip())
    except FileNotFoundError:
        pass
    # Create csv file with headers if it doesn't exist
    try:
        with open('data.txt', 'r', encoding='utf-8') as f:
            pass
    except FileNotFoundError:
        with open('data.csv', 'w', encoding='utf-8') as f:
            f.write('"Title"\t"Series"\t"Contributors"\t"Average Rating"\t"Number of Ratings"\t"Number of Reviews"\t"Description"\t"Number of Pages"\t"Publishing Date"\t"Genres"\t"Setting"\t"Characters"\t"URL"\n')
    url = book
    # count = 0
    # Start scraping loop
    while url is not None:
        url = clean_url(url)
        page = get_page(driver, url)
        data, next = scrape(page, url, scraped, crawling)
        # Log data to csv
        with open('data.csv', 'a', encoding='utf-8') as f:
            f.write(data)
        # Log book id to scraped file
        with open('scraped.txt', 'a', encoding='utf-8') as f:
            f.write(id(url) + '\n')
        scraped.add(id(url))
        url = next
        count += 1
    print(f'Next: {url}')
    print(f'Scraped {count} new books.')
    print('Scraping complete. No more new books found.')
    print('Consider starting again from a different book URL to explore more.')
    driver.quit()