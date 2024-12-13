# live.py

from flask import Flask, render_template_string
import asyncio
from scraper import Scraper

# Initialize Flask app
app = Flask(__name__)

# HTML template for displaying videos
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Links</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #121212; color: #e0e0e0; padding: 1rem; }
        h1 { font-size: 2rem; color: #fff; margin-bottom: 1rem; }
        .video-container { background: #1e1e1e; margin-bottom: 1rem; padding: 0.5rem; border-radius: 4px; }
        h2 { font-size: 1.2rem; color: #a0a0a0; margin: 0.3rem 0 0.5rem; }
        video { width: 100%; height: auto; border-radius: 4px; }
    </style>
</head>
<body>
    {% for video in videos %}
        <div class="video-container">
            <h2>{{ video.title }}</h2>
            <video controls>
                <source src="{{ video.file }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
    {% endfor %}
</body>
</html>
"""

async def fetch_videos(base_url: str):
    """Fetch videos using Scraper."""
    async with Scraper(base_url) as scraper:
        videos = await scraper.scrape()
        return [video for video in videos if video]

def launch_browser(base_url: str):
    """Launch a browser with scraped videos."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    videos = loop.run_until_complete(fetch_videos(base_url))

    @app.route('/')
    def index():
        return render_template_string(HTML_TEMPLATE, videos=videos)

    app.run(debug=True)
  
