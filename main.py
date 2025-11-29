''' Scrape book data from Goodreads starting from a given book URL.
    Extract title, series, contributors, and related book links.
    Save data to CSV and track scraped books to avoid duplicates.'''
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pathlib import Path
from time import sleep

book_url = 'https://www.goodreads.com/book/show/157993.The_Little_Prince'
index_url = 'https://www.goodreads.com/list/show/1.Best_Books_Ever'
goodreads_url = 'https://www.goodreads.com'

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
    with open('debug/book.html', 'w', encoding='utf-8') as f:
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
    book_details_soup = soup.select_one('.BookDetails')
    isbn = 'Unknown'
    language = 'Unknown'
    if book_details_soup is not None:
        book_details_list = book_details_soup.select('.DescListItem')
        for detail in book_details_list:
            detail_text = detail.get_text(strip=True)
            if 'Format' in detail_text:
                number_of_pages = detail_text.split('Format')[1].split(' ')[0].strip()
            if 'Published' in detail_text:
                publishing_date = detail_text.split('Published')[1].split('by')[0].strip()
            if 'ISBN' in detail_text:
                isbn = detail_text.split('ISBN')[1].replace('(', '').strip()
            if 'Language' in detail_text:
                language = detail_text.split('Language')[1].strip()
    # Get next page
    next = None
    if crawling:
        next = crawl(soup, scraped)
    csv_line = f'"{title}"\t"{series}"\t"{contributors_str}"\t"{average_rating}"\t"{number_of_ratings}"\t"{number_of_reviews}"\t"{description}"\t"{number_of_pages}"\t"{publishing_date}"\t"{genres_str}"\t"{setting}"\t"{characters}"\t"{isbn}"\t"{language}"\t"{url}"\n'
    return csv_line, next

def get_page(driver, url):
    ''' Open page and act to load full content '''
    driver.get(url)
    sleep(1)  # Wait for overlay to appear
    # Try removing overlay
    try:
        overlay_button = driver.find_element(By.CLASS_NAME, 'Overlay').find_element(By.CLASS_NAME, 'Button')
        overlay_button.click()
    except:
        pass
    # Scroll to book details section to load content
    details_button_element = driver.find_element(By.CLASS_NAME, 'BookDetails').find_element(By.CLASS_NAME, 'Button')
    ActionChains(driver).scroll_to_element(details_button_element).perform()
    try:
        details_button_element.click()
    except:
        pass
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

def extract_data(driver, url, scraped, crawling):
    ''' Extract data from a single book URL '''
    url = clean_url(url)
    page = get_page(driver, url)
    data, next = scrape(page, url, scraped, crawling)
    # Log data to csv
    with open('data.csv', 'a', encoding='utf-8') as f:
        f.write(data)
    # Log book id to scraped file
    with open('scraped.txt', 'a', encoding='utf-8') as f:
        f.write(id(url) + '\n')
    # Save page
    with open(f'pages/{id(url)}.html', 'w', encoding='utf-8') as f:
        f.write(page)
    scraped.add(id(url))
    return next

def get_books_from_index(driver, index_url, scraped):
    ''' Get list of book URLs from index page '''
    driver.get(index_url)
    page = driver.page_source
    soup = BeautifulSoup(page, 'html.parser')
    # For debugging, save the page locally
    with open('debug/index.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    # Get book URLs
    book_list = soup.select_one('.tableList').select('.bookTitle')
    books = []
    for book_element in book_list:
        book_url = book_element.get('href')
        book_url = clean_url(book_url)
        if id(book_url) not in scraped:
            books.append(goodreads_url + book_url)
    # Get next index page URL
    next_index = None
    next_button = soup.select_one('.next_page')
    if next_button is not None and 'disabled' not in next_button.get('class', []):
        next_index = goodreads_url + next_button.get('href')
    return books, next_index

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--book', type=str, help='If set, start from book URL')
    parser.add_argument('--index', type=str, help='If set, start from index URL')
    parser.add_argument('--crawl', help='If set, crawl related books', default=False, action='store_true')
    parser.add_argument('--crawl-limit', type=int, help='Limit for crawling related books', default=10)
    parser.add_argument('--show', help='If set, shows interactive browser', default=False, action='store_true')
    args = parser.parse_args()
    book = args.book
    index = args.index
    crawling = args.crawl
    crawl_limit = args.crawl_limit
    show = args.show
    if book is None and index is None:
        print('Please provide either a starting book URL or an index URL.')
        exit(1)
    # Set up Selenium WebDriver
    chrome_options = Options()
    if not show:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
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
        with open('data.csv', 'r', encoding='utf-8') as f:
            pass
    except FileNotFoundError:
        with open('data.csv', 'w', encoding='utf-8') as f:
            f.write('"Title"\t"Series"\t"Contributors"\t"Average Rating"\t"Number of Ratings"\t"Number of Reviews"\t"Description"\t"Number of Pages"\t"Publishing Date"\t"Genres"\t"Setting"\t"Characters"\t"ISBN"\t"Language"\t"URL"\n')
    # Ensure output directories exists
    Path("pages").mkdir(exist_ok=True)
    Path("debug").mkdir(exist_ok=True)
    # Scrape from book URL
    count = 0
    i = 0
    while book is not None and i < crawl_limit:
        print(f'{count+1}: Scraping {book}')
        next = extract_data(driver, book, scraped, crawling)
        book = next
        count += 1
        i += 1
    # Scrape from index URL
    while index is not None:
            print(f'Index: {index}')
            books, next_index = get_books_from_index(driver, index, scraped)
            for book in books:
                i = 0
                while book is not None and i < crawl_limit:
                    print(f'Book {count+1}: {book}')
                    next = extract_data(driver, book, scraped, crawling)
                    book = next
                    count += 1
                    i += 1
            index = next_index
    print(f'Scraping complete. Found {count} new books.')
    print('For more book consider starting again from a different URL.')
    driver.quit()