import argparse
import asyncio
from scraper import Scraper
from downloader import Downloader
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape and download videos from a given URL.")
    parser.add_argument("url", type=str, help="The base URL of the page to scrape.")
    parser.add_argument(
        "--download_folder",
        type=str,
        default="./downloads",
        help="Folder where the videos will be downloaded. Default is './downloads'."
    )
    return parser.parse_args()

async def scrape_videos(base_url: str):
    """Scrape video metadata from the given URL."""
    async with Scraper(base_url) as scraper:
        videos = await scraper.scrape()
        return videos

def download_videos(videos, download_folder):
    """Download videos using the Downloader."""
    downloader = Downloader(videos, download_folder)
    downloader.process_queue()

async def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Step 1: Scrape video links and metadata from the provided URL
    logger.info(f"Starting to scrape videos from {args.url}...")
    videos = await scrape_videos(args.url)

    if not videos:
        logger.error("No videos found. Exiting.")
        return

    # Step 2: Download the scraped videos
    logger.info(f"Found {len(videos)} videos. Starting download...")
    download_videos(videos, args.download_folder)

if __name__ == "__main__":
    try:
        # Run the main function
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script terminated by user.")
      
