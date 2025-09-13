# This patch adds crawling support into the GUI background loop
def crawl_and_learn(self, url):
    from seedai_crawler import WebCrawler
    crawler = WebCrawler()
    content = crawler.crawl(url)
    if content:
        self.reasoner.memory.extract_unknown_words(content)
        return f'Crawled and processed: {url}'
    else:
        return f'Failed to crawl: {url}'

# Example of triggering it
# response = self.crawl_and_learn("https://example.com")