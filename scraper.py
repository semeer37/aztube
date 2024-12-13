# scraper.py

import aiohttp
from aiohttp import ClientError
from aiohttp_proxy import ProxyConnector
from bs4 import BeautifulSoup
import re
import random
from typing import List, Dict, Optional
from proxy import ProxyManager
from logger import get_logger, clear_screen
from fake_useragent import UserAgent

# Initialize logger
logger = get_logger(__name__)

MAX_RETRIES = 3

class Scraper:
    def __init__(self, base_url: str, use_proxy: bool = False):
        self.base_url = base_url
        self.use_proxy = use_proxy
        self.video_links: List[str] = []
        self.videos: List[Dict[str, str]] = []
        self.proxies: List[str] = []
        self.current_proxy_index = 0

    async def __aenter__(self):
        if self.use_proxy:
            logger.info("Fetching working proxies...")
            self.proxies = ProxyManager.get_working_proxies()
            if not self.proxies:
                logger.error("No working proxies found. Proceeding without proxy.")
                self.use_proxy = False
            else:
                logger.info(f"Loaded {len(self.proxies)} working proxies.")
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_next_proxy(self) -> Optional[str]:
        """Rotate through proxies."""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy

    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from the target URL."""
        headers = {"User-Agent": UserAgent().random}

        for attempt in range(MAX_RETRIES):
            proxy = self.get_next_proxy() if self.use_proxy else None
            connector = ProxyConnector.from_url(f"http://{proxy}") if proxy else None

            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                try:
                    async with session.get(url, timeout=10) as response:
                        response.raise_for_status()
                        logger.info(f"Fetched {url} successfully.")
                        return await response.text()
                except ClientError as e:
                    logger.error(f"Request failed for {url} using proxy {proxy}. Error: {e}")
                    if proxy and self.use_proxy:
                        self.proxies.remove(proxy)
                        logger.warning(f"Removed failed proxy {proxy} from the list.")
        logger.error(f"Failed to fetch {url} after {MAX_RETRIES} retries.")
        return None

    async def find_video_links(self) -> List[str]:
        """Find video links on the target page."""
        html_content = await self.fetch_html(self.base_url)
        if not html_content:
            logger.warning(f"No HTML content found at {self.base_url}.")
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        video_links = soup.find_all("a", class_="video animate-thumb tt show-clip")
        self.video_links = [link.get("href") for link in video_links]
        return self.video_links

    async def extract_metadata(self, video_link: str) -> Optional[Dict[str, str]]:
        """Extract metadata for a single video link."""
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
        sources_regex = re.findall(
            r'{\s*file:\s*"(.*?)",\s*label:\s*"(.*?)",\s*default:\s*"(true|false)"\s*}', 
            playlist_content
        )

        metadata = {
            "title": title_regex.group(1) if title_regex else "",
            "file": next((source[0] for source in sources_regex if source[2] == "true"), ""),
        }
        return metadata

    async def scrape(self) -> List[Dict[str, str]]:
        """Perform the entire scraping process."""
        clear_screen()
        logger.info("Starting the scraping process...")
        self.video_links = await self.find_video_links()

        if not self.video_links:
            logger.warning("No video links found. Exiting scraping process.")
            return []

        metadata_tasks = [self.extract_metadata(link) for link in self.video_links]
        self.videos = await asyncio.gather(*metadata_tasks)
        return self.videos
