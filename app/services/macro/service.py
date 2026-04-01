import asyncio
import logging
from datetime import datetime, timedelta
import urllib.request
import json
import re
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

from app.services.macro.collectors import fetch_fred_indicators, fetch_rss_news, fetch_naver_journalist_news

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.macro_analysis import MacroAnalysisReport
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


def get_gemini_api_key_from_db() -> str | None:
    """
    DB의 SystemConfig 테이블에서 Gemini API 키를 동적으로 읽어옵니다.
    DB에 키가 없으면 .env의 GEMINI_API_KEY를 폴백으로 사용합니다.
    """
    db = SessionLocal()
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_api_key"
        ).first()
        if config:
            api_key = config.config_value.get("api_key", "")
            if api_key:
                logger.debug("Gemini API key loaded from DB SystemConfig.")
                return api_key
    except Exception as e:
        logger.warning(f"Failed to load Gemini API key from DB: {e}")
    finally:
        db.close()

    # Fallback: .env / 환경변수
    if settings.GEMINI_API_KEY:
        logger.debug("Gemini API key loaded from .env / environment variable.")
        return settings.GEMINI_API_KEY

    return None

async def extract_naver_finance_insight() -> dict:
    """
    Extract AI Summary and Global Rankings from Naver Finance Desktop using Playwright.
    """
    ai_summary_text = ""
    global_ranking_source = ""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://stock.naver.com/", wait_until="networkidle")
            
            try:
                await page.wait_for_selector('div[class*="HomeAiMarketInsights_home-ai-market-insights"]', timeout=5000)
                ai_element = await page.query_selector('div[class*="HomeAiMarketInsights_home-ai-market-insights"]')
                if ai_element:
                    ai_summary_text = await ai_element.inner_text()
                    logger.info("Successfully extracted Naver AI Market Insights")
            except Exception as e:
                logger.warning(f"Could not find Naver AI Market Insights: {e}")

            try:
                await page.wait_for_selector('div[class*="GlobalStockRanking_global-stock-ranking"]', timeout=5000)
                ranking_element = await page.query_selector('div[class*="GlobalStockRanking_global-stock-ranking"]')
                if ranking_element:
                    global_ranking_source = await ranking_element.inner_text()
                    logger.info("Successfully extracted Naver Global Stock Ranking")
            except Exception as e:
                logger.warning(f"Could not find Naver Global Stock Rankings: {e}")
                
            await browser.close()
    except Exception as e:
        logger.error(f"Error during Naver Finance extraction: {e}")
        
    return {
        "ai_summary": ai_summary_text.strip(),
        "global_ranking": global_ranking_source.strip()
    }

async def fetch_hk_global_youtube() -> dict:
    """
    Fetch the latest YouTube video transcript from the #모닝루틴 hashtag.
    """
    hashtag = "%EB%AA%A8%EB%8B%9D%EB%A3%A8%ED%8B%B4" 
    url = f"https://www.youtube.com/hashtag/{hashtag}"
    transcript_text = ""
    video_title = "오늘의 모닝루틴 영상"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        match = re.search(r'"videoId":"([^"]+)"', html)
        if not match:
            logger.error("Could not find any video ID for #모닝루틴")
            return {"title": "", "transcript": ""}
            
        video_id = match.group(1)
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript_fetched = transcript_list.find_transcript(['ko', 'en']).fetch()
            transcript_text = ' '.join([entry.text for entry in transcript_fetched])
            logger.info(f"Successfully processed YouTube video ID: {video_id} for #모닝루틴")
        except Exception as transcript_err:
            logger.error(f"Failed to fetch transcript: {transcript_err}")
            transcript_text = ""
    except Exception as e:
        logger.error(f"Error extracting #모닝루틴 YouTube transcript: {e}")
        
    return {
        "title": video_title,
        "transcript": transcript_text
    }

async def generate_macro_report(naver_data: dict, youtube_data: dict, fred_data: dict, rss_news: list, journalist_news: list) -> str:
    api_key = get_gemini_api_key_from_db()
    if not api_key:
        logger.error("Gemini API key is not configured in DB or .env.")
        return "⚠️ 오류: 중앙 서버에 Gemini API 키가 설정되지 않았습니다."

    genai.configure(api_key=api_key)
    # Hardcoded for quota stability
    model_name = "gemini-2.5-flash"
    print(f"DEBUG: Using Gemini model: {model_name}")
    logger.info(f"Using Gemini model: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        today_str = datetime.now().strftime("%Y.%m.%d")
        
        prompt = f"""
당신은 최고의 헤지펀드 거시경제 애널리스트입니다. 
제공되는 다양한 소스 데이터를 분석하여, {today_str} 기준 가장 직관적이고 통찰력있는 통합 거시경제 분석 리포트를 Markdown 포맷으로 작성해주세요.

## 1. 네이버 증시 실시간 요약 (Source)
{naver_data.get('ai_summary', '(데이터 없음)')}

## 2. 네이버 글로벌 증시 랭킹 (Source)
{naver_data.get('global_ranking', '(데이터 없음)')}

## 3. 한국투자증권 글로벌 마켓 시황 영상 (Source: {youtube_data.get('title', '제목 없음')})
{youtube_data.get('transcript', '(영상 자막 없음)')[:15000]}

## 4. 글로벌 매크로 지표 (FRED)
{json.dumps(fred_data, ensure_ascii=False) if fred_data else "(데이터 없음)"}

## 5. 해외 주요 실시간 뉴스 (RSS: Reuters, CNBC, WSJ)
{json.dumps(rss_news, ensure_ascii=False) if rss_news else "(뉴스 없음)"}

## 6. 국내 전문기자 지정학/경제 분석 (Source: 파이낸셜뉴스 중동전문)
{json.dumps(journalist_news, ensure_ascii=False) if journalist_news else "(뉴스 없음)"}

---

### 작성 지침:
1. 리포트는 반드시 아래 세 섹션 순서대로 작성하세요:

   [섹션 1] 📈 글로벌 매크로 분석
   모든 소스를 종합하여 현재 시장의 핵심 흐름을 분석합니다.
   
   - **주요 지표 및 시황**: 금리, 물가, 환율 등의 추이와 시장에 미치는 영향 분석
   - **지정학적 리스크**: 중동 전쟁(이란, 이스라엘) 등 주요 분쟁 상황과 파급 효과
   - **시장 전망**: 종합적인 데이터 기반 향후 흐름 예측

   출처는 언급하지 말고, 전문적인 리포트체(~합니다)로 작성하세요.

   [섹션 2] 🏆 당일 핵심 주도 테마 브리핑
   당일 강세/약세 섹터를 3~5개 선정하여 아래 포맷 준수:
   
   [섹터명]
   - 종목A (국가) (±X.X%): 한 줄 설명
   - 종목B (국가) (±X.X%): 한 줄 설명
   ※ 섹터 강세/약세 배경: 1~2줄 요약

   [섹션 3] ⚠️ 투자 주의 사항
   위 분석을 기반으로 투자 시 반드시 유의해야 할 포인트 3가지를 번호 목록으로 작성하세요.

2. 모든 문장은 '~합니다', '~입니다'와 같이 정중한 리포트체로 마무리하세요.
3. 볼드체(`**텍스트**`)는 절대 사용하지 마세요.
"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Failed to generate Macro Report: {e}")
        return f"AI 종합 분석 중 오류가 발생했습니다: {str(e)}"

async def execute_macro_analysis_cycle():
    logger.info("🌀 Starting Macro Analysis Data Pipeline...")
    
    naver_data = await extract_naver_finance_insight()
    youtube_data = await fetch_hk_global_youtube()
    fred_data = await fetch_fred_indicators()
    rss_news = await fetch_rss_news()
    journalist_news = await fetch_naver_journalist_news()
    
    report_content = await generate_macro_report(naver_data, youtube_data, fred_data, rss_news, journalist_news)
    
    db = SessionLocal()
    try:
        new_report = MacroAnalysisReport(
            naver_source_text=f"Summary: {naver_data['ai_summary']}\nRankings: {naver_data['global_ranking']}"[:5000],
            youtube_source_text=youtube_data['transcript'][:5000],
            report_content=report_content
        )
        db.add(new_report)
        db.commit()
        logger.info(f"✅ Executed and saved Macro Analysis Report id={new_report.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save MacroAnalysisReport to DB: {e}")
    finally:
        db.close()
