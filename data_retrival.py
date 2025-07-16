
# yt_data.py
# This script retrieves YouTube video data using the YouTube Data API v3.
import os
import requests
import  pandas as pd
from dotenv import load_dotenv
from typing import List, Optional


def get_top_videos(topic: str, api_key: Optional[str] = None) -> List[str]:
    """
    Queries the YouTube Data API to retrieve up to `n_res` video IDs related to the given `topic`.

    Args:
        topic (str): Search keyword or topic to look up on YouTube.
        max_res (int): Number of desired video results (API limit to 50).
        api_key (str, optional): YouTube Data API key.

    Returns:
        List[str]: A list of YouTube video IDs related to the topic.
    """
    search_url = "https://www.googleapis.com/youtube/v3/search"
    videos: List[str] = []        
    
    params = {
        "part": "snippet",
        "q": topic,
        "type": "video",
        "maxResults": 50,  # API limit
        "order": "Relevance",
        "key": api_key,
    }
    
    res =requests.get(search_url, params=params).json()
    items = res.get("items", [])
    videos.extend(item['id']['videoId'] for item in items if 'videoId' in item['id'])
    
    return videos 


def get_all_comments(video_id, api_key):
    """
    Retrieves all comments for a given YouTube video ID using the YouTube Data API v3.

    Args:
        video_id (str): The YouTube video ID to retrieve comments for.
        api_key (str): A valid YouTube Data API key.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing comment details such as author,
                              text, and publication date.
    """
    comments = []
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 100,
        "textFormat": "plainText",
        "key": api_key
    }
    
    response = requests.get(url, params=params).json()
    items = response.get("items", [])
    
    for item in items:
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "author": snippet["authorDisplayName"],
            "text": snippet["textDisplay"],
            "published_at": snippet["publishedAt"]
        })

    return comments


def run(youtube_dir: str, api_key: str) -> None:
    """
    Retrieves comments from the top YouTube videos related to a given topic,
    and saves them into a CSV file in the specified directory.

    Args:
        youtube_dir (str): The directory path where the output CSV will be saved.
        api_key (str): A valid YouTube Data API key.

    Returns:
        None
    """
    # Example topic and max results
    topic = "Crimes war in Gaza" 
    videos_ids = get_top_videos(topic, api_key)
    comments = list()
    for video_id in videos_ids:
        print(f"Retrieving comments for video ID: {video_id}")
        # Retrieve comments for each video ID
        video_comments = get_all_comments(video_id, api_key)
        comments.extend(video_comment for video_comment in video_comments)
    
    # Save videos comments to CSV
    if comments:
        comments_df = pd.DataFrame(comments)
        comments_df.to_csv(os.path.join(youtube_dir, f"{topic}_comments.csv"), index=False)
        print(f"Comments saved to {youtube_dir}/{topic.replace(" ", "_")}_comments.csv")


def main():
    # Load API
    load_dotenv()
    API_KEY = os.getenv("YT_API_KEY")
    if not API_KEY:
        raise ValueError("YouTube API key not found. Please set the YT_API_KEY environment variable.")

    # Directory to save data
    os.makedirs("Raw_data", exist_ok=True)
    youtube_dir = "Raw_data"

    run(youtube_dir, API_KEY)
    print("YouTube data retrieval complete.")


if __name__ == "__main__":
    main()

