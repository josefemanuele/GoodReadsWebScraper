''' Scrape book data from Goodreads starting from a given book URL.
    Extract title, series, contributors, and related book links.
    Save data to CSV and track scraped books to avoid duplicates.'''
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import re
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
    re_rating_statistics= re.compile(r'([0-9,]*)[ratings\s]*([0-9,]*)[reviews\s]*')
    re_date = re.compile(r'[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}')
    re_pages = re.compile('([0-9]+) pages?')
    re_isbn = re.compile('ISBN(.*)')
    re_language = re.compile('Language(.*)')
    # Save page for debugging
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
    rating_statistics_meta = rating_section.select_one('.RatingStatistics__meta').get_text(strip=True)
    rating_statistics_groups = re_rating_statistics.search(rating_statistics_meta)
    number_of_ratings = rating_statistics_groups.group(1)
    number_of_reviews = rating_statistics_groups.group(2)
    description = soup.select_one('.DetailsLayoutRightParagraph').get_text(strip=True)
    featured_details = soup.select_one('.FeaturedDetails').select('p')
    number_of_pages = 'Unknown'
    publishing_date = 'Unknown'
    for featured_detail in featured_details:
        featured_detail_text = featured_detail.get_text(strip=True)
        # Search number of pages
        match = re_pages.search(featured_detail_text)
        if match is not None:
            number_of_pages = match.group(1)
        # Search date
        match = re_date.search(featured_detail_text)
        if match is not None:
            publishing_date = match.group(0)
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
                setting = detail.select_one('.TruncatedContent__text').get_text(strip=True)
            if 'Characters' in detail_text:
                characters = detail.select_one('.TruncatedContent__text').get_text(strip=True)
    book_details_soup = soup.select_one('.BookDetails')
    isbn = 'Unknown'
    language = 'Unknown'
    if book_details_soup is not None:
        book_details_list = book_details_soup.select('.DescListItem')
        for detail in book_details_list:
            detail_text = detail.get_text(strip=True)
            # Search number of pages
            match = re_pages.search(detail_text)
            if match is not None:
                number_of_pages = match.group(1)
            # Search date
            match = re_date.search(detail_text)
            if match is not None:
                publishing_date = match.group(0)
            match = re_isbn.search(detail_text)
            if match is not None:
                isbn = match.group(1)
            match = re_language.search(detail_text)
            if match is not None:
                language = match.group(1)
                # Skip non-English books
                if language != 'English':
                    return None, None
    # Get next page
    next = None
    if crawling:
        next = crawl(soup, scraped)
    csv_line = f'"{title}"\t"{series}"\t"{contributors_str}"\t"{average_rating}"\t"{number_of_ratings}"\t"{number_of_reviews}"\t"{description}"\t"{number_of_pages}"\t"{publishing_date}"\t"{genres_str}"\t"{setting}"\t"{characters}"\t"{isbn}"\t"{language}"\t"{url}"\n'
    return csv_line, next

def get_page(driver, url):
    ''' Open page and act to load full content '''
    driver.get(url)
    # page = driver.page_source
    # soup = BeautifulSoup(page, 'html.parser')
    # with open('debug/book.html', 'w', encoding='utf-8') as f:
    #     f.write(soup.prettify())
    # Wait for overlay to appear
    sleep(1)
    # Check if page is not found
    title = driver.find_element(By.TAG_NAME, 'title').get_attribute('text')  
    if 'Page not found' in title:
        return None
    # Check overlay
    try:
        overlay_button = driver.find_element(By.CLASS_NAME, 'Overlay').find_element(By.CLASS_NAME, 'Button')
        overlay_button.click()
    except:
        pass
    # Scroll to book details section to load content
    details_button_element = driver.find_element(By.CLASS_NAME, 'BookDetails').find_element(By.CLASS_NAME, 'Button')
    ActionChains(driver).scroll_to_element(details_button_element).perform()
    details_button_element.click()
    # Scroll to related books section to load content
    related_element = driver.find_element(By.CLASS_NAME, 'BookPage__relatedTopContent')
    ActionChains(driver).scroll_to_element(related_element).perform()
    # Wait for content to load
    sleep(1)
    page = driver.page_source
    return page

def clean_url(url):
    ''' Get rid of query parameters '''
    return url.split('?')[0]

def id(url):
    ''' Get unique id from url '''
    return url.split('/')[-1]

def write_to_output_files(data, page, url):
    ''' Write data to output files '''
    # Save data to csv
    with open('data.csv', 'a', encoding='utf-8') as f:
        f.write(data)
    # Save book id to scraped file
    with open('scraped.txt', 'a', encoding='utf-8') as f:
        f.write(id(url) + '\n')
    # Save page
    with open(f'pages/{id(url)}.html', 'w', encoding='utf-8') as f:
        f.write(page)
    return

def extract_data(driver, url, scraped, crawling = False, testing = False, force = False):
    ''' Extract data from a single book URL '''
    url = clean_url(url)
    if not force:
        # Check if already scraped
        if id(url) in scraped:
            print(f'Page already scraped: {url}')
            return None
    page = get_page(driver, url)
    if page is None:
        print(f'Page not found: {url}')
        return None
    data, next = scrape(page, url, scraped, crawling)
    if data is None:
        # Skip non-English books
        return None
    # If testing, print data
    if testing:
        print(data)
    # Log data to csv
    else:
        write_to_output_files(data, page, url)
        # Add book id to scraped set
        scraped.add(id(url))
    return next

def get_books_from_index(driver, index_url):
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
    parser.add_argument('--test', help='If set, does not write on output datasets', default=False, action='store_true')
    parser.add_argument('--force', help='If set, force scraping even if already scraped', default=False, action='store_true')
    args = parser.parse_args()
    book = args.book
    index = args.index
    crawling = args.crawl
    crawl_limit = args.crawl_limit
    show = args.show
    testing = args.test
    force = args.force
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
        next = extract_data(driver, book, scraped, crawling, testing, force)
        book = next
        count += 1
        i += 1
    # Scrape from index URL
    while index is not None:
            print(f'Index: {index}')
            books, next_index = get_books_from_index(driver, index)
            for book in books:
                i = 0
                while book is not None and i < crawl_limit:
                    print(f'Book {count+1}: {book}')
                    next = extract_data(driver, book, scraped, crawling, testing, force)
                    book = next
                    count += 1
                    i += 1
            index = next_index
    print(f'Scraping complete. Scraped {count} books.')
    print('For more books consider starting again from a different URL.')
    driver.quit()