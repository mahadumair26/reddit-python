"""FastAPI dependencies."""

from src.scrapers.reddit_scraper import RedditScraper

scraper = RedditScraper()


def get_reddit_scraper() -> RedditScraper:
    """Dependency provider for scraper service."""
    return scraper
