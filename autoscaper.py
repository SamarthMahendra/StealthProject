from autoscraper import AutoScraper

url = 'https://jobs.careers.microsoft.com/global/en/search?l=en_us&pg=1&pgSz=20'

wanted = ['Principal Product Manager, Copilot', 'Data Center Construction Site Director - Zaragoza']
scraper = AutoScraper()
result = scraper.build(url, wanted)
print(result)