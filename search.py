#search.py

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Search:
    """
    A class to handle searching on a website.

    Attributes:
    ----------
    BASE_URL : str
        The base URL of the website.
    SEARCH_URL : str
        The URL used for searching on the website.
    session : aiohttp.ClientSession
        The aiohttp client session used for making requests.
    query : str
        The search query.
    results : list
        The search results.
    """

    BASE_URL = 'https://www.aznude.com'
    SEARCH_URL = 'https://search.aznude.com/?q='

    def __init__(self, session: aiohttp.ClientSession, query: str) -> None:
        """
        Initializes the Search class.

        Args:
        ----
        session : aiohttp.ClientSession
            The aiohttp client session used for making requests.
        query : str
            The search query.
        """
        self.session = session
        self.query = query
        self.results = []

    async def fetch_results(self) -> list:
        """
        Fetches the search results from the website.

        Returns:
        -------
        list
            The search results.
        """
        search_url = self.SEARCH_URL + '+'.join(self.query.split())
        try:
            async with self.session.get(search_url, timeout=10) as response:
                response.raise_for_status()
                html = await response.text()
                logging.info(f"Fetched results for query: {self.query}")
                return self.parse_results(html)
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching results: {e}")
            print("Error: Unable to fetch results. Please check your internet connection or try again later.")
            return []

    def parse_results(self, html: str) -> list:
        """
        Parses the HTML content to extract the search results.

        Args:
        ----
        html : str
            The HTML content.

        Returns:
        -------
        list
            The search results.
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        for box in soup.select('.story-thumbs.celebs-boxes'):
            link_tag = box.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = 'https:' + href if href.startswith('//') else href
                
                name_tag = box.find('h4')
                name = name_tag.get_text() if name_tag else 'Unknown'

                img_tag = box.find('img', src=True)
                img_src = img_tag['src'] if img_tag else 'No image available'
                full_img_src = 'https:' + img_src if img_src.startswith('//') else img_src

                results.append({'url': full_url, 'name': name, 'img': full_img_src})
        return results

    def display_results(self) -> None:
        """
        Displays the search results.
        """
        if not self.results:
            print("No results found for your query.")
            return

        print(f"Found {len(self.results)} result(s):")
        for i, result in enumerate(self.results):
            print(f"{i + 1}. {result['name']:<20} - {result['img']}")

    def choose_result(self) -> str | None:
        """
        Allows the user to choose a result.

        Returns:
        -------
        str | None
            The chosen result URL or None if no result is chosen.
        """
        if not self.results:
            return None

        if len(self.results) == 1:
            print(f"Only one result found: {self.results[0]['name']} - {self.results[0]['url']}")
            return self.results[0]['url']

        self.display_results()

        while True:
            try:
                choice = int(input("Enter the number of the result you want to select (or 0 to cancel): "))
                if choice == 0:
                    return None
                if 1 <= choice <= len(self.results):
                    return self.results[choice - 1]['url']
                else:
                    print(f"Invalid choice. Please enter a number between 1 and {len(self.results)}.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

    async def search(self) -> str | None:
        """
        Performs the search and returns the chosen result URL.

        Returns:
        -------
        str | None
            The chosen result URL or None if no result is chosen.
        """
        self.results = await self.fetch_results()
        return self.choose_result()

async def main() -> None:
    """
    The main function.
    """
    async with aiohttp.ClientSession() as session:
        while True:
            query = input("Enter the celebrity/movie name (or type 'exit' to quit): ").strip()
            if query.lower() == 'exit':
                print("Exiting the program.")
                break

            if query:
                search = Search(session, query)  # Pass the session to the Search instance
                url = await search.search()  # Use await to call the asynchronous search method
                if url:
                    print(f"Selected URL: {url}")
                else:
                    print("No valid URL was selected.")
            else:
                print("Query cannot be empty. Please enter a valid celebrity name.")

if __name__ == "__main__":
    asyncio.run(main())  # Run the asynchronous main function
