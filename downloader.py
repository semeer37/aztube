# downloader.py

import os
import requests
from urllib.parse import urlparse
from tqdm import tqdm
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from proxy import ProxyManager
from logger import get_logger, clear_screen

# Initialize logger
logger = get_logger(__name__)

class Downloader:
    MAX_RETRY_ATTEMPTS = 3
    MAX_WORKERS = 5

    def __init__(self, videos: List[Dict[str, str]], download_folder: str = "./downloads", use_proxy: bool = False):
        self.download_folder = download_folder
        self.videos = videos
        self.use_proxy = use_proxy
        self.proxies: List[str] = []
        self.proxy_index = 0
        self.session = requests.Session()

        if use_proxy:
            logger.info("Fetching proxies...")
            self.proxies = ProxyManager.get_working_proxies()
            if not self.proxies:
                logger.error("No working proxies found. Proceeding without proxy.")
                self.use_proxy = False
            else:
                logger.info(f"Loaded {len(self.proxies)} working proxies.")

    def get_next_proxy(self) -> Dict[str, str]:
        """Rotate and return the next working proxy."""
        if not self.proxies:
            return None
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    def download_video(self, video: Dict[str, str]):
        url = video["file"]
        filename = f"{video['title']}{os.path.splitext(urlparse(url).path)[1]}"
        download_path = os.path.join(self.download_folder, filename)

        os.makedirs(self.download_folder, exist_ok=True)
        proxies = self.get_next_proxy() if self.use_proxy else None

        try:
            response = self.session.get(url, stream=True, proxies=proxies, timeout=10)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            with open(download_path, "wb") as file, tqdm(
                total=total_size, unit="B", unit_scale=True, desc=filename, leave=False
            ) as progress:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        progress.update(len(chunk))

            logger.info(f"Downloaded {filename} successfully.")

        except requests.RequestException as e:
            logger.error(f"Error downloading {filename}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while downloading {filename}: {e}")

    def process_queue(self):
        """Process download queue."""
        logger.info("Starting download process...")

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            for video in self.videos:
                executor.submit(self.download_video, video)

# Example usage
def main():
    videos = [
        {"title": "Sample Video 1", "file": "https://example.com/sample1.mp4"},
        {"title": "Sample Video 2", "file": "https://example.com/sample2.mp4"},
    ]
    downloader = Downloader(videos, use_proxy=True)
    downloader.process_queue()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
        
