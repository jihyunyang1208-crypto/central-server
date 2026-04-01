import urllib.request
import re
from youtube_transcript_api import YouTubeTranscriptApi

def test_youtube():
    hashtag = "%EB%AA%A8%EB%8B%9D%EB%A3%A8%ED%8B%B4" # "모닝루틴" url encoded
    url = f"https://www.youtube.com/hashtag/{hashtag}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        print("Fetching HTML...")
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        # 1. Grab first videoId from the search results
        match = re.search(r'"videoId":"([^"]+)"', html)
        if not match:
            print("Could not find any video ID for #모닝루틴")
            return
            
        video_id = match.group(1)
        print(f"Found video ID: {video_id}")
        
        # 2. Grab transcript
        print("Fetching transcript...")
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id).find_transcript(['ko', 'en']).fetch()
            transcript_text = ' '.join([entry.get('text', '') for entry in transcript_list])
            print("TRANSCRIPT PREVIEW:", transcript_text[:100], "...")
        except Exception as transcript_err:
            print(f"Failed to fetch transcript: {transcript_err}")
            
    except Exception as e:
        print(f"Error extracting #모닝루틴 YouTube: {e}")

test_youtube()
