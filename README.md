# WebScraper on GoodReads
This project contains a Python script that runs a web scraping algorithm over www.goodreads.com

Goodreads.com is a public repository of text books, ratings and reviews. It is a valuable source of metadata on books.
The Python script extracts information such as Title, Series, Authors and so on, saving the data onto the data.csv output dataset.

## Usage:
Launch the script as: ``` python main.py --url [starting_point url] ```

The script will visit the provided page, extract and store the information, and continue with the first book in the 
"Suggested books" section which has not visited already.

This project was made as an assistance task for the course of "Algorithmic Methods for Data Mining", held at "La Sapienza" University of Rome.
