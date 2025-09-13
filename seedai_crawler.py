
import requests
from bs4 import BeautifulSoup

class WebCrawler:
    def __init__(self):
        self.visited = set()

    def crawl(self, url, max_pages=1):
        print(f"[Crawler] Starting crawl: {url}")
        if url in self.visited:
            return ""
        self.visited.add(url)

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"[Crawler] Failed to fetch {url} with status {response.status_code}")
                return ""
        except Exception as e:
            print(f"[Crawler] Exception while fetching {url}: {e}")
            return ""

        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=' ', strip=True)
        return text
