import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

def test_yt():
    hashtag = urllib.parse.quote("모닝루틴")
    url = f"https://www.youtube.com/hashtag/{hashtag}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        # looking for "videoId":"..."
        matches = re.finditer(r'"videoId":"([^"]+)"', html)
        video_ids = []
        for match in matches:
            vid = match.group(1)
            if vid not in video_ids:
                video_ids.append(vid)
                
        print(f"Found video IDs: {video_ids[:5]}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yt()
