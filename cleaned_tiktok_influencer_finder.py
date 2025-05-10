import os
import argparse
import json
import pandas as pd
import time
import random
import requests
from datetime import datetime
import sys

class TikTokAPI:
    """Simple TikTok API wrapper using the unofficial TikTok API endpoints"""
    
    def __init__(self, ms_token=None):
        self.base_url = "https://www.tiktok.com/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
            "Cookie": f"msToken={ms_token}" if ms_token else ""
        }
    
    def search_users(self, keyword, count=30, offset=0):
        """Search for users based on keyword"""
        try:
            url = f"{self.base_url}/search/user/full/"
            params = {
                "aid": "1988",
                "app_name": "tiktok_web",
                "device_platform": "web",
                "keyword": keyword,
                "count": count,
                "cursor": offset
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "userInfo" not in data or "user_list" not in data["userInfo"]:
                print(f"Warning: Unexpected API response format for keyword '{keyword}'")
                return []
            
            return data["userInfo"]["user_list"]
        
        except requests.RequestException as e:
            print(f"Error searching for '{keyword}': {str(e)}")
            return []
    
    def get_user_info(self, username):
        """Get detailed user information"""
        try:
            url = f"{self.base_url}/user/detail/"
            params = {
                "aid": "1988",
                "app_name": "tiktok_web",
                "device_platform": "web",
                "uniqueId": username
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "userInfo" not in data:
                print(f"Warning: Unable to fetch info for user '{username}'")
                return None
            
            return data["userInfo"]
        
        except requests.RequestException as e:
            print(f"Error getting info for '{username}': {str(e)}")
            return None
    
    def get_user_videos(self, sec_uid, count=30, cursor=0):
        """Get user's videos"""
        try:
            url = f"{self.base_url}/post/item_list/"
            params = {
                "aid": "1988",
                "app_name": "tiktok_web",
                "device_platform": "web",
                "count": count,
                "cursor": cursor,
                "secUid": sec_uid,
                "type": 1
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "itemList" not in data:
                print(f"Warning: Unable to fetch videos for user with secUid '{sec_uid}'")
                return []
            
            return data["itemList"]
        
        except requests.RequestException as e:
            print(f"Error getting videos: {str(e)}")
            return []

def search_influencers_by_keyword(api, keyword, max_results=100):
    """Search for influencers using a keyword"""
    print(f"Searching for '{keyword}' influencers...")
    
    all_users = []
    offset = 0
    batch_size = 30  # TikTok API typically returns 30 results per page
    
    with total=max_results, desc=f"Finding {keyword} creators") as pbar:
        while len(all_users) < max_results:
            users = api.search_users(keyword, count=batch_size, offset=offset)
            
            if not users:
                break
                
            all_users.extend(users)
            pbar.update(len(users))
            
            offset += len(users)
            
            # Avoid rate limiting
            time.sleep(random.uniform(1.0, 2.0))
    
    # Remove duplicates based on secUid
    unique_users = {user["user"]["secUid"]: user for user in all_users}
    
    print(f"Found {len(unique_users)} unique accounts for '{keyword}'")
    return list(unique_users.values())

def filter_influencers(api, users, max_followers=550000, min_avg_views=40000, niche=""):
    """Filter influencers based on follower count and analyze their videos"""
    qualified_influencers = []
    
    with total=len(users), desc="Analyzing accounts") as pbar:
        for user_data in users:
            user = user_data["user"]
            username = user["uniqueId"]
            sec_uid = user["secUid"]
            follower_count = int(user.get("followerCount", 0))
            
            # Check follower count
            if follower_count > max_followers:
                pbar.update(1)
                continue
            
            # Get videos to analyze average views
            videos = api.get_user_videos(sec_uid, count=30)
            
            if not videos:
                pbar.update(1)
                continue
            
            # Calculate average views
            total_views = sum(int(video["stats"]["playCount"]) for video in videos)
            avg_views = total_views / len(videos)
            
            # Check minimum average views
            if avg_views >= min_avg_views:
                influencer_data = {
                    "username": username,
                    "displayName": user.get("nickname", ""),
                    "bio": user.get("signature", ""),
                    "followerCount": follower_count,
                    "followingCount": int(user.get("followingCount", 0)),
                    "videoCount": int(user.get("videoCount", 0)),
                    "avgViews": avg_views,
                    "verified": user.get("verified", False),
                    "secUid": sec_uid,
                    "niche": niche,
                    "profileUrl": f"https://www.tiktok.com/@{username}"
                }
                
                qualified_influencers.append(influencer_data)
                print(f"Qualified: {username} - {follower_count:,} followers, {avg_views:,.2f} avg views")
            
            pbar.update(1)
            
            # Avoid rate limiting
            time.sleep(random.uniform(1.0, 2.0))
    
    return qualified_influencers

def find_tiktok_influencers(keywords, max_followers=550000, min_avg_views=40000, ms_token=None, results_per_keyword=50):
    """Find TikTok influencers matching criteria across multiple keywords"""
    api = TikTokAPI(ms_token)
    all_influencers = []
    
    for keyword in keywords:
        print(f"\nSearching for influencers in the '{keyword}' niche...")
        
        # Search for users related to the keyword
        users = search_influencers_by_keyword(api, keyword, max_results=results_per_keyword)
        
        # Filter and analyze the users
        qualified = filter_influencers(api, users, max_followers, min_avg_views, keyword)
        all_influencers.extend(qualified)
        
        print(f"Found {len(qualified)} qualified influencers for '{keyword}'")
    
    # Remove duplicates based on username
    unique_influencers = {inf["username"]: inf for inf in all_influencers}
    return list(unique_influencers.values())

def main():
    parser = argparse.ArgumentParser(description='Find TikTok influencers based on criteria')
    parser.add_argument('--keywords', nargs='+', default=['AI', 'tech', 'business'], 
                        help='Keywords to search for influencers')
    parser.add_argument('--max_followers', type=int, default=550000,
                       help='Maximum follower count')
    parser.add_argument('--min_avg_views', type=int, default=40000,
                       help='Minimum average views per video')
    parser.add_argument('--output', default='tiktok_influencers.csv',
                       help='Output CSV file name')
    parser.add_argument('--ms_token', default=None,
                       help='TikTok msToken for API access (optional)')
    parser.add_argument('--results_per_keyword', type=int, default=50,
                       help='Maximum number of results to process per keyword')
    
    args = parser.parse_args()
    
    print("\nTikTok Influencer Finder")
    print("=======================")
    print(f"Searching for influencers in these niches: {', '.join(args.keywords)}")
    print(f"Criteria: Under {args.max_followers:,} followers, with at least {args.min_avg_views:,} average views per video")
    print("=======================\n")
    
    try:
        qualified_influencers = find_tiktok_influencers(
            args.keywords,
            args.max_followers,
            args.min_avg_views,
            args.ms_token,
            args.results_per_keyword
        )
        
        if not qualified_influencers:
            print("No influencers found matching the criteria.")
            return
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(qualified_influencers)
        df = df.sort_values(by="avgViews", ascending=False)
        
        # Rearrange columns for output
        columns = [
            "username", "displayName", "followerCount", "avgViews", 
            "videoCount", "niche", "bio", "verified", "profileUrl", "secUid"
        ]
        df_output = df[columns]
        
        # Rename columns for better readability
        column_names = {
            "username": "Username",
            "displayName": "Display Name",
            "followerCount": "Followers",
            "avgViews": "Avg Views",
            "videoCount": "Videos",
            "niche": "Niche",
            "bio": "Bio",
            "verified": "Verified",
            "profileUrl": "Profile URL",
            "secUid": "Sec UID"
        }
        df_output = df_output.rename(columns=column_names)
        
        df_output.to_csv(args.output, index=False)
        print(f"\nFound {len(qualified_influencers)} matching influencers. Results saved to {args.output}")
        
        # Also save a pretty summary to text file
        txt_output = args.output.replace('.csv', '.txt')
        with open(txt_output, 'w', encoding='utf-8') as f:
            f.write("TikTok Influencer Finder Results\n")
            f.write("===============================\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Search Keywords: {', '.join(args.keywords)}\n")
            f.write(f"Criteria: Under {args.max_followers:,} followers, with at least {args.min_avg_views:,} average views per video\n\n")
            f.write(f"Found {len(qualified_influencers)} matching influencers:\n\n")
            
            for i, inf in enumerate(qualified_influencers, 1):
                f.write(f"{i}. @{inf['username']} ({inf['displayName']})\n")
                f.write(f"   Followers: {inf['followerCount']:,}\n")
                f.write(f"   Avg Views: {inf['avgViews']:,.2f}\n")
                f.write(f"   Videos: {inf['videoCount']}\n")
                f.write(f"   Niche: {inf['niche']}\n")
                f.write(f"   Verified: {'Yes' if inf['verified'] else 'No'}\n")
                f.write(f"   Profile: {inf['profileUrl']}\n")
                
                # Split bio into lines if too long
                bio = inf['bio'].strip()
                if bio:
                    if len(bio) > 70:
                        f.write(f"   Bio: {bio[:70]}...\n")
                    else:
                        f.write(f"   Bio: {bio}\n")
                
                f.write("\n")
        
        print(f"A detailed summary is also available at {txt_output}")
        
    except KeyboardInterrupt:
        print("\nSearch interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main()