import asyncio
import logging
import feedparser
import requests
import json
from bs4 import BeautifulSoup
from app.core.config import settings

logger = logging.getLogger(__name__)

async def fetch_fred_indicators() -> dict:
    """
    Fetch major US economic indicators from FRED.
    """
    if not settings.FRED_API_KEY:
        logger.warning("FRED_API_KEY not set in central-backend.")
        return {}
        
    series_ids = {
        "FEDFUNDS": "미국 연방기금금리",
        "CPIAUCSL": "미국 소비자물가지수(CPI)",
        "GDP": "미국 국내총생산(GDP)",
        "UNRATE": "미국 실업률"
    }
    
    results = {}
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    for sid, name in series_ids.items():
        try:
            params = {
                "series_id": sid,
                "api_key": settings.FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1
            }
            # Run in thread since requests is blocking
            response = await asyncio.to_thread(requests.get, base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                obs = data.get("observations", [])
                if obs:
                    results[name] = obs[0]["value"]
        except Exception as e:
            logger.error(f"Error fetching FRED series {sid}: {e}")
            
    return results

async def fetch_rss_news() -> list:
    """
    Fetch global business news from RSS feeds with multi-language keyword filtering.
    """
    feeds = [
        {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?best-topics=business&post_type=best"},
        {"name": "CNBC Finance", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=401&id=10000664"},
        {"name": "WSJ Markets", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"}
    ]
    
    # Priority keywords for filtering
    target_keywords = ["stock", "market", "interest", "economy", "war", "iran", "israel", "geopolitical", "risk", "oil"]
    
    all_articles = []
    for f in feeds:
        try:
            # Run feedparser in thread as it's blocking
            feed = await asyncio.to_thread(feedparser.parse, f['url'])
            for entry in feed.entries[:15]:
                title = entry.title
                summary = entry.get('summary', entry.get('description', ''))
                text = (title + " " + summary).lower()
                
                if any(k in text for k in target_keywords):
                    all_articles.append({
                        "source": f['name'],
                        "title": title,
                        "url": entry.link
                    })
        except Exception as e:
            logger.error(f"Error fetching RSS {f['name']}: {e}")
            
    return all_articles[:10]

async def fetch_naver_journalist_news(journalist_url: str = "https://media.naver.com/journalist/014/24706") -> list:
    """
    Fetch news from a specific Naver journalist page.
    """
    articles = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Use sync requests in thread as it's blocking
        response = await asyncio.to_thread(requests.get, journalist_url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Naver journalist page: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selectors identified via browser subagent
        news_items = soup.select('li.press_edit_news_item')
        
        # Keywords for filtering
        target_keywords = ["전쟁", "이란", "이스라엘", "중동", "지정학", "리스크", "유가", "금리", "경제"]
        
        for item in news_items:
            link_tag = item.select_one('a.press_edit_news_link')
            title_tag = item.select_one('span.press_edit_news_title')
            
            if link_tag and title_tag:
                title = title_tag.text.strip()
                url = link_tag.get('href', '')
                
                # Filter by keyword
                if any(k in title for k in target_keywords):
                    articles.append({
                        "source": "금융뉴스 전문기자",
                        "title": title,
                        "url": url
                    })
                    
        logger.info(f"Fetched {len(articles)} relevant articles from Naver journalist page.")
    except Exception as e:
        logger.error(f"Error fetching Naver journalist news: {e}")
        
    return articles[:10]
