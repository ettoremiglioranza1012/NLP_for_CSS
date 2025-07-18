
# yt_data.py
# This script retrieves YouTube video data using the YouTube Data API v3.
"""
            +----------------+
            | Configuration  |
            +----------------+
                    |
            +----------------+
            | main()         |
            | - Flags check  |
            | - Load .env    |
            +----------------+
            /                \
      +---------+        +----------+
      | YouTube |        |  Reddit  |
      +---------+        +----------+
           |                  |
     get_top_videos()   run_reddit()
           |                  |
  get_all_comments()   extract_reddit_comments()
           |                  |
     run_youtube()     save_reddit_comments()
           |                  |
     merge_all_data()     merge to fftext_data.csv
           |
     save as CSV

"""
import os
import time
import requests
import requests.auth 
import  pandas as pd
from typing import List
from dotenv import load_dotenv
from datetime import datetime, timezone


def get_top_videos(topic: str, api_key: str, max_results: int) -> List[str]:
    """
    Queries the YouTube Data API to retrieve up to `n_res` video IDs related to the given `topic`.
    """
    search_url = "https://www.googleapis.com/youtube/v3/search"
    videos: List[str] = []        
    
    params = {
        "part": "snippet",
        "q": topic,
        "type": "video",
        "maxResults": max_results,  # API limit
        "order": "Relevance",
        "key": api_key,
    }
    
    res =requests.get(search_url, params=params).json()
    items = res.get("items", [])
    videos.extend(item['id']['videoId'] for item in items if 'videoId' in item['id'])
    
    return videos 


def get_all_comments(video_id: str, api_key: str, max_resutls: int) -> List[dict[str, str]]:
    """
    Retrieves all comments for a given YouTube video ID using the YouTube Data API v3.
    """
    comments = []
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_resutls,  # API limit
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


def merge_all_data(dfs: list[pd.DataFrame]) -> None:
    """Merge all CSVs into a single file""" 
    # Fixed variables
    ffname = "fftext_data.csv"
    db_dir_name = "Data_MLReady"
    
    # Directory to save data
    os.makedirs(db_dir_name, exist_ok=True)
    
    # Full path for the output file
    ffpath = os.path.join(db_dir_name, ffname)
    
    try:
        # Verify existence
        if os.path.exists(ffpath):
            ff = pd.read_csv(ffpath)
        else:
            # Initialise empty DataFrame
            ff = pd.DataFrame()

        # Loop over the different files in the list and concatenate
        for curr_df in dfs:
            # Concatenate with main DataFrame
            ff = pd.concat([ff, curr_df], ignore_index=True)
        
        # Save to csv
        ff.to_csv(ffpath, index=False)
        print("Data correctly concatenated to final db")
    except Exception as e:
        print(f"An error occurred while merging data: {e}")

    
def run_youtube(api_key: str, topics: list[str], config: dict[str, int]) -> None:
    """
    Retrieves comments from the top YouTube videos related to a given topic,
    and saves them into a CSV file in the specified directory.
    """
    list_of_dfs = []
    for topic in topics:
        # Example topic and max results 
        videos_ids = get_top_videos(topic, api_key, config["max_results_video"])
        comments = list()
        for video_id in videos_ids:
            print(f"Retrieving comments for video ID: {video_id}")
            # Retrieve comments for each video ID
            video_comments = get_all_comments(video_id, api_key, config["max_results_comments"])
            comments.extend(video_comment for video_comment in video_comments)
        
        # Save videos comments to CSV
        if comments:
            comments_df = pd.DataFrame(comments)
            list_of_dfs.append(comments_df)
     
    merge_all_data(list_of_dfs)


def extract_reddit_comments(children: List[dict], min_score: int = 5) -> List[dict]:
    """
    Extracts posts from Reddit that have comments with a score above a specified threshold.
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


def csv_format_migration(all_data: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the comments of one Subreddit"""
    extracted_comments = list()
    for post in all_data:
        for comment in post.get("comments"):
            # i-th dict
            curr_row = dict()
            curr_row["author"] = comment.get("author", "")
            curr_row["text"] = comment.get("body", "")
            curr_row["published_at"] = comment.get("created_utc", "")
            extracted_comments.append(curr_row)
    return extracted_comments


def save_reddit_comments(comments: list[dict[str, str]]) -> None:
    """ Save Reddit comments to a CSV file."""
    # Fixed variables
    db_dir_name = "Data_MLReady"
    os.makedirs(db_dir_name, exist_ok=True)
    ffname = "fftext_data.csv"
    ffpath = os.path.join(db_dir_name, ffname)
    curr_df_comms = pd.DataFrame(comments)
    if os.path.exists(ffpath):
        origin_df = pd.read_csv(ffpath)
        origin_df = pd.concat([origin_df, curr_df_comms], ignore_index=True)
        origin_df.to_csv(ffpath, index=False)
    else:
        curr_df_comms.to_csv(ffpath, index=False)
    print("Table correctly updated.")


def run_reddit(
        client_id: str, 
        client_secret: str, 
        username: str, 
        password: str, 
        user_agent: str,
        subreddits: list[str],
        queries: list[str],
        config: dict[str, int]
) -> None:
    """
    Retrieves posts from Reddit related to a given topic and saves them into a CSV file.
    """
    for subreddit in subreddits:
        for query in queries:

            limit = config['limit']  # Set max number of posts to retrieve
            comment_score_min = config['comment_score_min']   # Score threshold

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
                created_utc = datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat()

                # Fetch comments for the post
                comments_url = f'https://oauth.reddit.com/comments/{post_id}'
                # Make the request to get comments
                response = requests.get(comments_url, headers=headers, params={'depth':10, 'limit': 500})
                comment_mass = response.json()[1].get('data', {}).get('children', [])
                # comment mass is a list of comments
                high_comments = extract_reddit_comments(comment_mass, min_score=comment_score_min)

                post_record = {
                        'post_id': post_id,
                        'created_utc': created_utc,
                        'comments': high_comments  # Store comments with score above threshold
                }

                all_data.append(post_record)
                print(f"(ID: {post_id}) with {len(high_comments)} comments above score {comment_score_min}")
                time.sleep(0.1)

            curr_list_of_comments = csv_format_migration(all_data)
            save_reddit_comments(curr_list_of_comments)

            
def main():
    # Video labels to search for (youtube)
    # These are the topics that will be used to search for videos and comments
    topics = [
        "Crime against humanity", 
        "War crimes", 
        "Bombing of hospitals", 
        "Rape in war", 
        "torture"
    ]
    topics = [topic + " Israel" for topic in topics]

    # Subreddit to search for
    subreddits = [
        "Palestine",
        "IsraelPalestine"
    ]

    queries = [
        "Crime against humanity", 
        "War crimes", 
        "Bombing of hospitals", 
        "Rape in war", 
        "torture"
    ]

    queries = [query + ' Israel' for query in queries]

    # Configuration flags
    # Set to True to enable data retrieval from YouTube and Reddit
    # Set to False to skip data retrieval
    flags = {
        'YT' : True,
        'REDDIT' : True
    }

    # Data Scraping Configuration
    scraping_config = {
        'YT': {
            'max_results_video': 50,  # Max results per topic (limit at 50 by YouTube API)
            'max_results_comments': 100  # Max comments per video (limit at 100 by YouTube API)
        },

        'REDDIT': {
            'limit': 1000,  # Max posts to retrieve
            'comment_score_min': 5  # Minimum score for comments to be included
        }
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

    try:
        if flags['YT']:
            # Start YouTube data retrieval
            print("Starting YouTube data retrieval...")
            run_youtube(API_KEY, topics, scraping_config['YT'])
            print("YouTube data retrieval complete.")
        else:
            print("YouTube data retrieval is disabled. Skipping...")
        
        if flags['REDDIT']:
            # Start Reddit data retrieval
            print("Starting Reddit data retrieval...")
            run_reddit(
                client_id, 
                client_secret, 
                username, 
                password, 
                user_agent, 
                subreddits, 
                queries, 
                scraping_config['REDDIT']
            )
            print("Reddit data retrieval complete.")
        else:
            print("Reddit data retrieval is disabled. Skipping...")
    except Exception as e:
        print(f"An error occurred during data retrieval: {e}")
        raise  
    finally:
        print("\nData retrieval process completed.\n")


if __name__ == "__main__":
    main()


