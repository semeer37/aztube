# scraper.py
import asyncio
import aiohttp
from aiohttp import ClientError
from aiohttp_retry import RetryClient, ExponentialRetry
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict, Optional

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self, base_url: str):
        self.base_url: str = base_url
        self.video_links: List[str] = []
        self.videos: List[Dict[str, str]] = []

    async def __aenter__(self):
        retry_options = ExponentialRetry(attempts=3)
        self.session = RetryClient(retry_options=retry_options)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def fetch_html(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except ClientError as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    async def find_video_links(self) -> List[str]:
        html_content = await self.fetch_html(self.base_url)
        if not html_content:
            logger.warning(f"No HTML content found at {self.base_url}.")
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        video_links = soup.find_all("a", class_="video animate-thumb tt show-clip")
        self.video_links = [link.get("href") for link in video_links]
        return self.video_links

    async def extract_metadata(self, video_link: str) -> Optional[Dict[str, str]]:
        url = f"https://www.aznude.com{video_link}"
        html_content = await self.fetch_html(url)
        if not html_content:
            logger.warning(f"No HTML content found at {url}. Skipping metadata extraction.")
            return None

        playlist_regex = re.search(r'playlist: \[(.*?)\],', html_content, re.DOTALL)
        if not playlist_regex:
            logger.warning(f"No playlist content found in HTML at {url}.")
            return None

        playlist_content = playlist_regex.group(1)
        title_regex = re.search(r'title:\s*"(.*?)"', playlist_content)
        thumbnail_regex = re.search(r'image:\s*"(.*?)"', playlist_content)
        sources_regex = re.findall(r'{\s*file:\s*"(.*?)",\s*label:\s*"(.*?)",\s*default:\s*"(true|false)"\s*}', playlist_content)

        metadata = {
            "title": title_regex.group(1) if title_regex else "",
            #"thumbnail": 'https:' + thumbnail_regex.group(1) if thumbnail_regex else "",
            "file": next((source[0] for source in sources_regex if source[2] == "true"), ""),
        }
        return metadata

    async def scrape(self) -> List[Dict[str, str]]:
        self.video_links = await self.find_video_links()
        if not self.video_links:
            logger.warning("No video links found. Exiting scraping process.")
            return []

        logger.info(f"Found {len(self.video_links)} Video Links:")
        for link in self.video_links:
            logger.info(link)

        metadata_tasks = [self.extract_metadata(link) for link in self.video_links]
        self.videos = await asyncio.gather(*metadata_tasks)
        return self.videos

# Example usage
async def main():
    base_url = "https://www.aznude.com/view/celeb/a/angelacremonte.html"
    async with Scraper(base_url) as scraper:
        videos = await scraper.scrape()

        logger.info("\nExtracted Metadata:")
        logger.info("----------------------")
        for video in videos:
            if video:

                logger.info(video)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script terminated by user.")
