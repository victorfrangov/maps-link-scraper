# Google Maps Website Lead Scraper

Simple Google Maps lead scraper using Selenium + ChromeDriver.

## Features
- Search Google Maps for a query
- Check business details and detect if only social links/websites are present
- CLI args: search query, max leads, optional `--headless`

## Usage

Synopsis:
```
python scraper.py [QUERY] [OPTIONS]
```

Arguments:
- QUERY
  - Optional positional search query (e.g. "Cafes in City, ST"). If omitted, the default from the script is used.

Options:
- --max, -m <INT>
  - Maximum number of leads to process. Default: 10
- --headless
  - Run Chrome in headless mode.
- -h, --help
  - Show help and exit.

## Notes
- This script drives the real browser — respect terms of service and rate limits.
- Adjust WAIT times in `scraper.py` if elements load slowly.
