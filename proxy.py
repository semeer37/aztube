# proxy.py

import asyncio
import aiohttp
from aiohttp_proxy import ProxyConnector
from fake_useragent import UserAgent
from typing import List

PROXY_TEST_URL = "https://httpbin.org/ip"

class ProxyManager:
    """Manages proxy fetching and validation with internal async logic."""

    @staticmethod
    async def _fetch_proxies() -> List[str]:
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

    @staticmethod
    async def _check_proxy(proxy: str) -> bool:
        """Check if a proxy is working."""
        connector = ProxyConnector.from_url(f"http://{proxy}")
        headers = {"User-Agent": UserAgent().random}

        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            try:
                async with session.get(PROXY_TEST_URL, timeout=5) as response:
                    return response.status == 200
            except Exception:
                return False

    @classmethod
    async def _get_working_proxies(cls) -> List[str]:
        """Fetch and validate working proxies."""
        proxies = await cls._fetch_proxies()
        tasks = [cls._check_proxy(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks)
        return [proxy for proxy, valid in zip(proxies, results) if valid]

    @classmethod
    def get_working_proxies(cls) -> List[str]:
        """Synchronous method to get working proxies."""
        return asyncio.run(cls._get_working_proxies())
      
