# downloader.py
import os
import logging
import requests
import queue
from urllib.parse import urlparse
from tqdm import tqdm
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_exponential
import itertools

def clear_screen():
    if os.name == 'nt':
        _ = os.system('cls')
    else:
        _ = os.system('clear')
        
# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class Downloader:
    MAX_RETRY_ATTEMPTS = 3
    MAX_WORKERS = 5

    def __init__(self, videos: List[Dict[str, str]], download_folder: str = "./downloads"):
        self.download_folder = download_folder
        self.video_queue = queue.Queue()
        self.retry_queue = queue.Queue()
        self.failed_downloads = set()

        for video in videos:
            self.video_queue.put(video)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def validate_url(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=5)
            response.raise_for_status()
            logger.info(f"Validated URL: {url}")
            return True
        except requests.RequestException as e:
            logger.error(f"Invalid URL {url}: {e}")
            return False

    def get_unique_filename(self, filename):
        base, ext = os.path.splitext(filename)
        for i in itertools.count(1):
            unique_filename = f"{base}_{i}{ext}"
            if not os.path.exists(os.path.join(self.download_folder, unique_filename)):
                return unique_filename

    def download_video(self, video: Dict[str, str]):
        url = video["file"]
        filename = f"{video['title']}{os.path.splitext(urlparse(url).path)[1]}"
        download_path = os.path.join(self.download_folder, filename)

        if os.path.exists(download_path):
            filename = self.get_unique_filename(filename)
            download_path = os.path.join(self.download_folder, filename)

        try:
            os.makedirs(self.download_folder, exist_ok=True)
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            if total_size == 0:
                logger.warning(f"Content-Length not available for {filename}. Downloading without progress tracking.")

            logger.info(f"Starting download: {filename} ({total_size / (1024**2):.2f} MB)" if total_size else f"Starting download: {filename}")

            with open(download_path, "wb") as file, tqdm(
                total=total_size if total_size else None, unit="B", unit_scale=True, desc=filename
            ) as progress:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        if total_size:
                            progress.update(len(chunk))

            logger.info(f"Downloaded {filename} successfully.")

        except requests.ConnectionError as e:
            logger.error(f"Connection error while downloading {filename}: {e}")
            self.retry_queue.put(video)
        except requests.Timeout as e:
            logger.error(f"Timeout error while downloading {filename}: {e}")
            self.retry_queue.put(video)
        except requests.RequestException as e:
            logger.error(f"Request error while downloading {filename}: {e}")
            self.retry_queue.put(video)
        except OSError as e:
            logger.error(f"File system error while saving {filename}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while downloading {filename}: {e}")
            self.retry_queue.put(video)

    def process_queue(self):
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            while not self.video_queue.empty():
                video = self.video_queue.get()
                if self.validate_url(video["file"]):
                    executor.submit(self.download_video, video)
                else:
                    logger.error(f"Skipping invalid URL: {video['file']}")

        self.retry_failed_downloads()

    def retry_failed_downloads(self):
        retry_attempt = 1

        while not self.retry_queue.empty() and retry_attempt <= self.MAX_RETRY_ATTEMPTS:
            logger.info(f"Retrying failed downloads - Attempt {retry_attempt}...")
            temp_queue = queue.Queue()

            with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                while not self.retry_queue.empty():
                    video = self.retry_queue.get()
                    executor.submit(self.download_video, video)
                    temp_queue.put(video)

            self.retry_queue = temp_queue
            retry_attempt += 1

        if self.retry_queue.empty():
            logger.info("All downloads completed successfully.")
        else:
            logger.error("Some downloads still failed after retries.")

# Example usage
def main():
    videos = [
        {"title": "ghosted", "file": "https://cdn2.aznude.com/8f69e5d094bc4133bf6854563139f0ca/8f69e5d094bc4133bf6854563139f0ca-hd.mp4"},
        {"title": "knock knock", "file": "https://cdn1.aznude.com/anadearmas/knockknock/KnockKnock-Izzo_Armas-HD-001-hd.mp4"},
        {"title": "Invalid Video", "file": "https://invalid-url.com/video.mp4"},
    ]

    downloader = Downloader(videos)
    downloader.process_queue()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
