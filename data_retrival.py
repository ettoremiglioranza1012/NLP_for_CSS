
# yt_data.py
# This script retrieves YouTube video data using the YouTube Data API v3.
import os
import time
import json
import requests
import requests.auth 
import  pandas as pd
from dotenv import load_dotenv
from typing import List, Optional
from datetime import datetime, timezone


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


def run_youtube(youtube_dir: str, api_key: str) -> None:
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


def extract_reddit_comments(children: List[dict], min_score: int = 5) -> List[dict]:
    """
    Extracts posts from Reddit that have comments with a score above a specified threshold.

    Args:
        posts (List[dict]): List of Reddit posts.
        min_score (int): Minimum score for comments to be included -> number of interactions
                         with the comment.

    Returns:
        List[dict]: Filtered list of posts with comments meeting the score criteria.
    """
    results = []
    for child in children:
        kind = child.get('kind')
        data = child.get('data', {})
        if kind != 't1':  # 't1' indicates a comment
            continue
        score = data.get('score', 0)
        body = data.get('body', '')
        # Check if the score meets the minimum threshold and the body is not empty or deleted
        if score >= min_score and not body.startswith('[deleted]') and body.strip():
            post = {
                'id': data.get('id'),
                'author': data.get('author'),
                'score': score,
                'created_utc': datetime.fromtimestamp(data.get('created_utc', 0), timezone.utc).isoformat(),
                'body': body
            }
            results.append(post)
        replies = data.get('replies', {})
        if replies and isinstance(replies, dict):
            # Recursively extract comments from replies
            results.extend(extract_reddit_comments(replies.get('data', {}).get('children', []), min_score))
    return results


def run_reddit(reddit_dir: str, client_id: str, client_secret: str, username: str, password: str, user_agent: str) -> None:
    """
    Retrieves posts from Reddit related to a given topic and saves them into a CSV file.

    Args:
        reddit_dir (str): The directory path where the output CSV will be saved.
        client_id (str): Reddit API client ID.
        client_secret (str): Reddit API client secret.
        username (str): Reddit username.
        password (str): Reddit password.
        user_agent (str): User agent for the Reddit API.

    Returns:
        None
    """
    # Example parameters
    subreddit = 'Palestine'
    query = "Israel's crime war"
    limit = 5000  # Set max number of posts to retrieve
    comment_score_min = 3   # Score threshold
    output_json = 'reddit_posts_with_comments.json'

    # Authenticate with Reddit API
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {'grant_type': 'password', 'username': username, 'password': password}
    headers = {'User-Agent': user_agent}

    # Get access token
    res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
    token = res.json().get('access_token')
    headers['Authorization'] = f'bearer {token}'

    # Search for posts in the specified subreddit
    search_url = f'https://oauth.reddit.com/r/{subreddit}/search'
    params = {
        'q': query,
        'limit': limit,
        'sort': 'relevance',
        'restrict_sr': True
    }
    
    # Make the request to Reddit API
    resp = requests.get(search_url, headers=headers, params=params)
    posts = resp.json().get('data', {}).get('children', [])

    # All data to be collected
    all_data = []

    # Process and filter posts
    for post in posts:
        post_data = post.get('data', {})
        post_id = post_data.get('id')
        title = post_data.get('title')
        selftext = post_data.get('selftext')
        score = post_data.get('score')
        author = post_data.get('author')
        created_utc = datetime.fromtimestamp(data.get('created_utc', 0)).isoformat()
        num_comments = post_data.get('num_comments')

        # Fetch comments for the post
        comments_url = f'https://oauth.reddit.com/comments/{post_id}'
        # Make the request to get comments
        response = requests.get(comments_url, headers=headers, params={'depth':10, 'limit': 500})
        comment_mass = response.json()[1].get('data', {}).get('children', [])
        # comment mass is a list of comments
        high_comments = extract_reddit_comments(comment_mass, min_score=comment_score_min)

        post_record = {
                'post_id': post_id,
                'title': title,
                'selftext': selftext,
                'score': score,
                'author': author,
                'created_utc': created_utc,
                'num_comments': num_comments,
                'comments': high_comments  # Store comments with score above threshold
        }

        all_data.append(post_record)
        print(f"Processed post: {title} (ID: {post_id}) with {len(high_comments)} comments above score {comment_score_min}")
        time.sleep(0.1)
        
    
    # Write to JSON file 
    if all_data:
        output_file = os.path.join(reddit_dir, output_json)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        print(f"Reddit posts with comments saved to {output_file}")
    

def main():
    # Configuration flags
    # Set to True to enable data retrieval from YouTube and Reddit
    # Set to False to skip data retrieval
    flags = {
        'YT' : False,
        'REDDIT' : True
    }

    # Load environment variables
    load_dotenv()

    # Get Youtube API
    API_KEY = os.getenv("YT_API_KEY")
    # Check if API key is set
    if not API_KEY:
        raise ValueError("YouTube API key not found. Please set the YT_API_KEY environment variable.")

    # Get Reddit API
    client_id=os.getenv("REDDIT_CLIENT_ID")
    client_secret=os.getenv("REDDIT_CLIENT_SECRET")
    username=os.getenv("REDDIT_USERNAME")
    password=os.getenv("REDDIT_PASSWORD")
    user_agent=os.getenv("REDDIT_USER_AGENT")
    # Check if Reddit API credentials are set
    if not all([client_id, client_secret, username, password, user_agent]):
        raise ValueError("Reddit API credentials not found. Please set the Reddit environment variables.")

    if flags['YT']:
        # Directory to save data
        os.makedirs("Raw_data_Youtube", exist_ok=True)
        youtube_dir = "Raw_data_Youtube"
        
        # Start YouTube data retrieval
        print("Starting YouTube data retrieval...")
        run_youtube(youtube_dir, API_KEY)
        print("YouTube data retrieval complete.")
    else:
        print("YouTube data retrieval is disabled. Skipping...")
    
    if flags['REDDIT']:
        # Directory to save data
        os.makedirs("Raw_Data_Reddit", exist_ok=True)
        reddit_dir = "Raw_Data_Reddit"
        
        # Start Reddit data retrieval
        print("Starting Reddit data retrieval...")
        run_reddit(reddit_dir, client_id, client_secret, username, password, user_agent)
        print("Reddit data retrieval complete.")
    else:
        print("Reddit data retrieval is disabled. Skipping...")


if __name__ == "__main__":
    main()

