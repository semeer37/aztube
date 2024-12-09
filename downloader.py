# downloader.py

import os
import requests
import queue
from urllib.parse import urlparse
from tqdm import tqdm
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_exponential
import itertools
from logger import get_logger, clear_screen

# Initialize logger
logger = get_logger(__name__)

class Downloader:
    """
    A video downloader that downloads video files from provided URLs using multithreading.

    Attributes:
        videos (List[Dict[str, str]]): List of video metadata with titles and file URLs.
        download_folder (str): The folder where videos will be downloaded.
        video_queue (queue.Queue): Queue holding videos to be downloaded.
        retry_queue (queue.Queue): Queue holding failed downloads for retry.
    """

    MAX_RETRY_ATTEMPTS = 3
    MAX_WORKERS = 5

    def __init__(self, videos: List[Dict[str, str]], download_folder: str = "./downloads"):
        """
        Initializes the Downloader class.

        Args:
            videos (List[Dict[str, str]]): List of video metadata to download.
            download_folder (str): Path to the folder where downloads will be saved.
        """
        self.download_folder = download_folder
        self.video_queue = queue.Queue()
        self.retry_queue = queue.Queue()

        for video in videos:
            self.video_queue.put(video)

    '''
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def validate_url(self, url: str) -> bool:
        """
        Validates a file URL by sending a HEAD request.

        Args:
            url (str): The file URL to validate.

        Returns:
            bool: True if the URL is valid, False otherwise.
        """
        try:
            response = requests.head(url, timeout=5)
            response.raise_for_status()
            logger.info(f"Validated URL: {url}")
            return True
        except requests.RequestException as e:
            logger.error(f"Invalid URL {url}: {e}")
            return False
    '''

    def get_unique_filename(self, filename: str) -> str:
        """
        Generates a unique filename if a file with the same name already exists.

        Args:
            filename (str): The original filename.

        Returns:
            str: A unique filename that doesn't exist in the download folder.
        """
        base, ext = os.path.splitext(filename)
        for i in itertools.count(1):
            unique_filename = f"{base}_{i}{ext}"
            if not os.path.exists(os.path.join(self.download_folder, unique_filename)):
                return unique_filename

    def download_video(self, video: Dict[str, str]):
        """
        Downloads a single video file from the provided video metadata.

        Args:
            video (Dict[str, str]): A dictionary containing video title and file URL.
        """
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
            
            clear_screen()
            
            total_size = int(response.headers.get("content-length", 0))
            with open(download_path, "wb") as file, tqdm(
                total=total_size, unit="B", unit_scale=True, desc=filename, leave=False
            ) as progress:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        progress.update(len(chunk))

            logger.warning(f"Downloaded {filename} successfully.")

        except requests.RequestException as e:
            logger.error(f"Error downloading {filename}: {e}")
            self.retry_queue.put(video)
        except OSError as e:
            logger.error(f"File system error while saving {filename}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while downloading {filename}: {e}")
            self.retry_queue.put(video)
    '''
    def process_queue(self):
        """
        Processes the download queue by validating URLs and downloading videos concurrently.
        """
        clear_screen()
        logger.info("Starting download process...")

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            while not self.video_queue.empty():
                video = self.video_queue.get()
                if self.validate_url(video["file"]):
                    executor.submit(self.download_video, video)
                else:
                    logger.error(f"Skipping invalid URL: {video['file']}")

        self.retry_failed_downloads()
    '''
    def process_queue(self):
        """
        Processes the download queue by validating URLs and downloading videos concurrently.
        """
        clear_screen()
        logger.info("Starting download process...")

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            while not self.video_queue.empty():
                video = self.video_queue.get()
                executor.submit(self.download_video, video)
                
        self.retry_failed_downloads()
        
    def retry_failed_downloads(self):
        """
        Retries downloads for videos that failed during the initial download attempt.
        """
        retry_attempt = 1

        while not self.retry_queue.empty() and retry_attempt <= self.MAX_RETRY_ATTEMPTS:
            logger.warning(f"Retrying failed downloads - Attempt {retry_attempt}...")
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
    """
    Example usage demonstrating how to initialize and run the Downloader class.
    """
    videos = [
        {"title": "ghosted", "file": "https://cdn2.aznude.com/sample_video_1.mp4"},
        {"title": "knock knock", "file": "https://cdn1.aznude.com/sample_video_2.mp4"},
        {"title": "Invalid Video", "file": "https://invalid-url.com/video.mp4"},
    ]

    downloader = Downloader(videos)
    downloader.process_queue()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
