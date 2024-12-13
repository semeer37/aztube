# main.py

import argparse
import asyncio
from scraper import Scraper
from downloader import Downloader
from logger import get_logger, clear_screen
from live import launch_browser

# Initialize logger
logger = get_logger(__name__)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Scrape and download videos from a given URL.")
    parser.add_argument("url", type=str, help="The base URL of the page to scrape.")
    parser.add_argument("--download_folder", type=str, default="./downloads", help="Download folder path.")
    parser.add_argument("--live", action="store_true", help="Display videos live in a web browser.")
    return parser.parse_args()

async def scrape_videos(base_url: str):
    """Scrape videos from the given URL."""
    async with Scraper(base_url) as scraper:
        videos = await scraper.scrape()
        return videos

def download_videos(videos, download_folder: str):
    """Download videos using the Downloader."""
    downloader = Downloader(videos, download_folder)
    downloader.process_queue()

async def main():
    args = parse_arguments()

    # Clear the terminal screen
    clear_screen()

    if args.live:
        logger.info(f"Launching live view for {args.url}...")
        launch_browser(args.url)
        return

    # Scrape and download videos
    logger.info(f"Starting to scrape videos from {args.url}...")
    videos = await scrape_videos(args.url)

    if not videos:
        logger.error("No videos found. Exiting.")
        return

    logger.info(f"Found {len(videos)} videos. Starting download...")
    download_videos(videos, args.download_folder)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script terminated by user.")
