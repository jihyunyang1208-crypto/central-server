import asyncio
from playwright.async_api import async_playwright

async def test_naver():
    try:
        async with async_playwright() as p:
            print("Launching browser...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print("Going to naver finance...")
            await page.goto("https://stock.naver.com/", wait_until="networkidle")
            
            print("Extracting AI Summary...")
            try:
                await page.wait_for_selector('div[class*="HomeAiMarketInsights_home-ai-market-insights"]', timeout=5000)
                ai_element = await page.query_selector('div[class*="HomeAiMarketInsights_home-ai-market-insights"]')
                if ai_element:
                    print("AI SUMMARY EXTRACTED:", await ai_element.inner_text())
                else:
                    print("AI Element not found")
            except Exception as e:
                print("Error extracting AI summary:", e)

            print("Extracting Global Ranking...")
            try:
                await page.wait_for_selector('div[class*="GlobalStockRanking_global-stock-ranking"]', timeout=5000)
                ranking_element = await page.query_selector('div[class*="GlobalStockRanking_global-stock-ranking"]')
                if ranking_element:
                    print("RANKING EXTRACTED:", await ranking_element.inner_text())
                else:
                    print("Ranking Element not found")
            except Exception as e:
                print("Error extracting global ranking:", e)
                
            await browser.close()
            
    except Exception as e:
        print("Fatal error:", e)

asyncio.run(test_naver())
