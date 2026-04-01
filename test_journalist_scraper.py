import asyncio
import sys
import os

# Set PYTHONPATH to the current directory
sys.path.append(os.getcwd())

from app.services.macro.collectors import fetch_naver_journalist_news

async def test():
    print("--- Testing Naver Journalist News Scraper ---")
    news = await fetch_naver_journalist_news()
    print(f"Relevant articles found: {len(news)}")
    for n in news:
        print(f"- {n['title']} ({n['url']})")

if __name__ == "__main__":
    asyncio.run(test())
