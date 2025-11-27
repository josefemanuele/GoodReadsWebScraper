# WebScraper on GoodReads
This project contains a Python script that runs a web scraping algorithm over www.goodreads.com

Goodreads.com is a public repository of text books, ratings and reviews. It is a valuable source of metadata on books.
The Python script extracts information such as Title, Authors, Ratings, and so on, saving the data onto the data.csv output dataset.

## Usage:
Launch the script as: ``` python main.py --url [starting_point url] ```

The script will visit the provided page, extract and store the information, and continue with the first book in the 
"Suggested books" section which has not visited already.

To test the script, just execute ``` python main.py ```. It will start the scraping from a default book url.

## Data:
The collected data is stored in the data.csv file. The format of the csv is:
Title, Series, Authors, Average rating, Number of ratings, Number of reviews, Description, Number of pages, Publishing date, Genres, Url.

In scraped.txt you can find all of the book urls that have been analysed.

This project was made as an assistance task for the course of "Algorithmic Methods for Data Mining", held at "La Sapienza" University of Rome.
