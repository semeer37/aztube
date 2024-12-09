# scraper.py

import asyncio
import aiohttp
from aiohttp import ClientError
from aiohttp_retry import RetryClient, ExponentialRetry
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from logger import get_logger, clear_screen

# Initialize logger
logger = get_logger(__name__)

class Scraper:
    """
    A web scraper for extracting video metadata from a specified base URL.

    Attributes:
        base_url (str): The URL of the web page to scrape.
        video_links (List[str]): List of video links found on the page.
        videos (List[Dict[str, str]]): Extracted metadata for each video.
    """

    def __init__(self, base_url: str):
        """
        Initializes the Scraper with the specified base URL.

        Args:
            base_url (str): The web page's base URL to scrape.
        """
        self.base_url: str = base_url
        self.video_links: List[str] = []
        self.videos: List[Dict[str, str]] = []

    async def __aenter__(self):
        """Initialize the async session with retry capabilities."""
        retry_options = ExponentialRetry(attempts=3)
        self.session = RetryClient(retry_options=retry_options)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the async session on exit."""
        await self.session.close()

    async def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetches the HTML content of a given URL asynchronously.

        Args:
            url (str): The URL to fetch the HTML from.

        Returns:
            Optional[str]: The HTML content as a string, or None if the request fails.
        """
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except ClientError as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    async def find_video_links(self) -> List[str]:
        """
        Finds video links on the base page.

        Returns:
            List[str]: A list of video link URLs found on the page.
        """
        html_content = await self.fetch_html(self.base_url)
        if not html_content:
            logger.warning(f"No HTML content found at {self.base_url}.")
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        video_links = soup.find_all("a", class_="video animate-thumb tt show-clip")
        self.video_links = [link.get("href") for link in video_links]
        return self.video_links

    async def extract_metadata(self, video_link: str) -> Optional[Dict[str, str]]:
        """
        Extracts metadata from a video page.

        Args:
            video_link (str): The relative link to the video page.

        Returns:
            Optional[Dict[str, str]]: Extracted metadata containing title and file URL.
        """
        url = f"https://www.aznude.com{video_link}"
        html_content = await self.fetch_html(url)
        if not html_content:
            logger.warning(f"No HTML content found at {url}. Skipping metadata extraction.")
            return None

        # Extract video playlist details
        playlist_regex = re.search(r'playlist: \[(.*?)\],', html_content, re.DOTALL)
        if not playlist_regex:
            logger.warning(f"No playlist content found in HTML at {url}.")
            return None

        playlist_content = playlist_regex.group(1)
        title_regex = re.search(r'title:\s*"(.*?)"', playlist_content)
        sources_regex = re.findall(r'{\s*file:\s*"(.*?)",\s*label:\s*"(.*?)",\s*default:\s*"(true|false)"\s*}', playlist_content)

        metadata = {
            "title": title_regex.group(1) if title_regex else "",
            "file": next((source[0] for source in sources_regex if source[2] == "true"), ""),
        }
        return metadata

    async def scrape(self) -> List[Dict[str, str]]:
        """
        Performs the full scraping process:
        - Finds video links on the base page.
        - Extracts metadata for each video link.

        Returns:
            List[Dict[str, str]]: A list of metadata dictionaries for all found videos.
        """
        clear_screen()
        logger.info("Starting the scraping process...")
        self.video_links = await self.find_video_links()

        if not self.video_links:
            logger.warning("No video links found. Exiting scraping process.")
            return []

        metadata_tasks = [self.extract_metadata(link) for link in self.video_links]
        self.videos = await asyncio.gather(*metadata_tasks)
        return self.videos

# Example usage
async def main():
    """
    Example async main function demonstrating how to use the Scraper class.
    """
    base_url = "https://www.aznude.com/view/celeb/a/angelacremonte.html"
    async with Scraper(base_url) as scraper:
        videos = await scraper.scrape()
        logger.info("Scraping completed.")
        for video in videos:
            if video:
                logger.info(video)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script terminated by user.")
        
