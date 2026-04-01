from youtube_transcript_api import YouTubeTranscriptApi
import sys

def test():
    video_id = "Ck8OVzcdlSI" # Sample video
    print(f"Type: {type(YouTubeTranscriptApi)}")
    print(f"Dir: {dir(YouTubeTranscriptApi)}")
    
    # Method 1: classmethod get_transcript
    try:
        print("Trying Method 1: YouTubeTranscriptApi.get_transcript(video_id)")
        tx = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        print(f"Success! Lines: {len(tx)}")
        return
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2: instance method get_transcript
    try:
        print("Trying Method 2: YouTubeTranscriptApi().get_transcript(video_id)")
        tx = YouTubeTranscriptApi().get_transcript(video_id, languages=['ko', 'en'])
        print(f"Success! Lines: {len(tx)}")
        return
    except Exception as e:
        print(f"Method 2 failed: {e}")

    # Method 3: list and fetch
    try:
        print("Trying Method 3: YouTubeTranscriptApi.list(video_id)")
        # If list is instance method
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        tx = transcript_list.find_transcript(['ko', 'en']).fetch()
        print(f"Success! Lines: {len(tx)}")
        print(f"Element type: {type(tx[0])}")
        print(f"First element: {tx[0]}")
        try:
             print(f"Text via .get(): {tx[0].get('text')}")
        except Exception as e:
             print(f"Text via .get() failed: {e}")
        try:
             print(f"Text via dictionary access: {tx[0]['text']}")
        except Exception as e:
             print(f"Text via dictionary access failed: {e}")
        return
    except Exception as e:
        print(f"Method 3 failed: {e}")

    # Method 4: Maybe just list(video_id) as class method without 'get_transcript' mapping?
    # But we saw it expects self.
    
    # Method 5: Check module level
    import youtube_transcript_api
    try:
        print("Trying Method 5: youtube_transcript_api.get_transcript(video_id)")
        tx = youtube_transcript_api.get_transcript(video_id, languages=['ko', 'en'])
        print(f"Success! Lines: {len(tx)}")
        return
    except Exception as e:
        print(f"Method 5 failed: {e}")

if __name__ == "__main__":
    test()
