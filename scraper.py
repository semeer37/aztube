# scraper.py

import asyncio
import aiohttp
from aiohttp import ClientError
from aiohttp_proxy import ProxyConnector
from bs4 import BeautifulSoup
import re
import random
from typing import List, Dict, Optional
from logger import get_logger, clear_screen
from fake_useragent import UserAgent

# Initialize logger
logger = get_logger(__name__)

PROXY_TEST_URL = "https://httpbin.org/ip"
MAX_RETRIES = 3

async def fetch_proxies() -> List[str]:
    """Fetches proxies from a free proxy provider."""
    url = "https://free-proxy-list.net/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            page = await response.text()
            soup = BeautifulSoup(page, "html.parser")
            table = soup.find("tbody")
            proxies = [
                f"{row.find_all('td')[0].text}:{row.find_all('td')[1].text}"
                for row in table if row.find_all('td')[4].text == 'elite proxy'
            ]
    return proxies

async def check_proxy(proxy: str) -> bool:
    """Check if a proxy is working."""
    connector = ProxyConnector.from_url(f"http://{proxy}")
    headers = {"User-Agent": UserAgent().random}

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        try:
            async with session.get(PROXY_TEST_URL, timeout=5) as response:
                if response.status == 200:
                    logger.info(f"Proxy {proxy} is working.")
                    return True
        except Exception as e:
            logger.error(f"Proxy {proxy} failed. Error: {e}")
    return False

async def get_working_proxies() -> List[str]:
    """Fetch and validate working proxies."""
    proxies = await fetch_proxies()
    tasks = [check_proxy(proxy) for proxy in proxies]
    results = await asyncio.gather(*tasks)
    return [proxy for proxy, valid in zip(proxies, results) if valid]

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
            self.proxies = await get_working_proxies()
            if not self.proxies:
                logger.error("No working proxies found. Disabling proxy usage.")
                self.use_proxy = False
            else:
                logger.info(f"Loaded {len(self.proxies)} working proxies.")
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_next_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy

    async def fetch_html(self, url: str) -> Optional[str]:
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
                    await asyncio.sleep(random.uniform(1, 3))  # Random delay to prevent blocking

        logger.error(f"Failed to fetch {url} after {MAX_RETRIES} retries.")
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
        clear_screen()
        logger.info("Starting the scraping process...")
        self.video_links = await self.find_video_links()

        if not self.video_links:
            logger.warning("No video links found. Exiting scraping process.")
            return []

        metadata_tasks = [self.extract_metadata(link) for link in self.video_links]
        self.videos = await asyncio.gather(*metadata_tasks)
        return self.videos
                    
