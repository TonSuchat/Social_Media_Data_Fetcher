"""
Facebook Graph API client for fetching page post analytics.
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass
from dateutil import parser as date_parser
import pytz

# Bangkok timezone (GMT+7)
BANGKOK_TZ = pytz.timezone('Asia/Bangkok')


@dataclass
class PostMetrics:
    """Standardized post metrics across all platforms."""
    post_id: str
    post_url: str
    platform: str
    created_time: datetime
    caption: str = ""  # Post text/name
    views: int = 0  # Total views (impressions)
    interactions: int = 0  # Total interactions (likes, comments, shares)
    reach: int = 0  # Unique viewers
    follows: int = 0  # New followers from this post
    link_clicks: int = 0  # Link clicks
    likes: int = 0
    comments: int = 0
    shares: int = 0
    
    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "post_url": self.post_url,
            "platform": self.platform,
            "date": self.created_time.strftime("%Y-%m-%d"),
            "time": self.created_time.strftime("%H:%M"),
            "caption": self.caption[:100] + "..." if len(self.caption) > 100 else self.caption,
            "views": self.views,
            "interactions": self.interactions,
            "reach": self.reach,
            "follows": self.follows,
            "link_clicks": self.link_clicks,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
        }


class FacebookAPI:
    """Client for Facebook Graph API to fetch page post analytics."""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token: str, page_id: str):
        """
        Initialize Facebook API client.
        
        Attributes:
            debug (bool): If True, print raw API responses for debugging.
        
        Args:
            access_token: Page Access Token with pages_read_engagement permission
            page_id: Facebook Page ID
        """
        self.access_token = access_token
        self.page_id = page_id
        self.session = requests.Session()
        self.debug = False  # Set to True to print raw API responses
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make authenticated request to Graph API."""
        params = params or {}
        params["access_token"] = self.access_token
        
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_page_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[dict]:
        """
        Fetch posts from the Facebook Page.
        
        Args:
            since: Only fetch posts created after this datetime
            limit: Maximum number of posts to fetch
            
        Returns:
            List of post data dictionaries
        """
        params = {
            "fields": "id,message,created_time,permalink_url,shares,full_picture",
            "limit": min(limit, 100),
        }
        
        if since:
            params["since"] = int(since.timestamp())
        
        posts = []
        endpoint = f"{self.page_id}/posts"
        
        while len(posts) < limit:
            data = self._make_request(endpoint, params)
            posts.extend(data.get("data", []))
            
            # Handle pagination
            paging = data.get("paging", {})
            if "next" in paging and len(posts) < limit:
                # Extract cursor for next page
                next_url = paging["next"]
                params["after"] = next_url.split("after=")[1].split("&")[0] if "after=" in next_url else None
                if not params.get("after"):
                    break
            else:
                break
        
        return posts[:limit]
    
    def get_post_insights(self, post_id: str, try_insights: bool = False) -> dict:
        """
        Fetch engagement metrics for a specific post.
        
        NOTE: Full insights (views, reach, impressions) require the 'read_insights' 
        permission which needs Facebook App Review approval.
        
        With just 'pages_read_engagement', we can get: reactions, comments, shares.
        
        Args:
            post_id: The Facebook post ID (format: {page_id}_{post_id})
            try_insights: If True, attempt to fetch insights (requires read_insights permission)
            
        Returns:
            Dictionary with engagement metrics
        """
        # Initialize defaults
        likes = 0
        comments = 0
        shares = 0
        views = 0
        reach = 0
        follows = 0
        link_clicks = 0
        
        # Only try insights endpoint if explicitly requested AND user has read_insights permission
        # Most users won't have this - it requires Facebook App Review
        if try_insights:
            try:
                insights_data = self._make_request(
                    f"{post_id}/insights",
                    params={
                        "metric": "post_impressions,post_impressions_unique,post_engaged_users,post_clicks"
                    }
                )
                
                for item in insights_data.get("data", []):
                    metric_name = item.get("name")
                    values = item.get("values", [{}])
                    value = values[0].get("value", 0) if values else 0
                    
                    if metric_name == "post_impressions":
                        views = value
                    elif metric_name == "post_impressions_unique":
                        reach = value
                    elif metric_name == "post_clicks":
                        link_clicks = value
                        
            except requests.HTTPError:
                pass  # Silently skip - user doesn't have read_insights permission
        
        # Get engagement counts (reactions, comments, shares)
        # Note: Page posts may require different query format
        
        # First try: query with just post ID (without page prefix) for reactions
        # Sometimes the full pageId_postId format doesn't work for reactions edge
        post_id_only = post_id.split("_")[-1] if "_" in post_id else post_id
        
        # Try querying reactions using just the post object ID
        try:
            post_data = self._make_request(
                post_id_only,
                params={
                    "fields": "shares,reactions.summary(total_count),comments.summary(total_count)"
                }
            )
            
            if self.debug:
                print(f"\n🔍 DEBUG - API Response for {post_id_only}:")
                print(f"   Raw data: {post_data}")
            
            likes = post_data.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = post_data.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = post_data.get("shares", {}).get("count", 0)
            
        except requests.HTTPError as e:
            if self.debug:
                print(f"\n🔍 DEBUG - Error for {post_id_only}: {e}")
            
            # Fallback: try with full post_id
            try:
                post_data = self._make_request(
                    post_id,
                    params={
                        "fields": "shares,reactions.summary(total_count),comments.summary(total_count)"
                    }
                )
                
                if self.debug:
                    print(f"\n🔍 DEBUG - API Response for {post_id}:")
                    print(f"   Raw data: {post_data}")
                
                likes = post_data.get("reactions", {}).get("summary", {}).get("total_count", 0)
                comments = post_data.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares = post_data.get("shares", {}).get("count", 0)
                
            except requests.HTTPError as e:
                if self.debug:
                    print(f"\n🔍 DEBUG - Error for {post_id}: {e}")
                # Try likes edge instead
                try:
                    post_data = self._make_request(
                        post_id,
                        params={
                            "fields": "shares,likes.summary(total_count),comments.summary(total_count)"
                        }
                    )
                    
                    likes = post_data.get("likes", {}).get("summary", {}).get("total_count", 0)
                    comments = post_data.get("comments", {}).get("summary", {}).get("total_count", 0)
                    shares = post_data.get("shares", {}).get("count", 0)
                    
                except requests.HTTPError:
                    # Last resort: just get shares
                    try:
                        post_data = self._make_request(post_id, params={"fields": "shares"})
                        shares = post_data.get("shares", {}).get("count", 0)
                    except:
                        pass
        
        return {
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "views": views,
            "reach": reach,
            "follows": follows,
            "link_clicks": link_clicks,
            "interactions": likes + comments + shares,
        }
    
    def get_posts_with_metrics(
        self,
        days: int = 7,
        since: Optional[datetime] = None
    ) -> list[PostMetrics]:
        """
        Fetch all posts with their metrics for the specified time period.
        
        Args:
            days: Number of days to look back (ignored if since is provided)
            since: Fetch posts created after this datetime
            
        Returns:
            List of PostMetrics objects
        """
        if since is None:
            since = datetime.now() - timedelta(days=days)
        
        posts = self.get_page_posts(since=since)
        results = []
        
        for post in posts:
            post_id = post["id"]
            created_time = date_parser.parse(post["created_time"]).astimezone(BANGKOK_TZ)
            caption = post.get("message", "")  # Post text/caption
            
            # Extract engagement data from post
            # Note: shares are always available
            # likes/reactions/comments require App Review for 'pages_read_engagement'
            shares = post.get("shares", {}).get("count", 0)
            
            # These require approved 'pages_read_engagement' permission (App Review)
            likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments_count = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            
            # Debug output if enabled
            if self.debug:
                print(f"\n🔍 DEBUG - Post {post_id}:")
                print(f"   shares: {post.get('shares', {})}")
                print(f"   (likes/comments require App Review)")
            
            # Calculate total interactions (only shares available without App Review)
            interactions = likes + comments_count + shares
            
            # Views/Reach require read_insights permission (also needs App Review)
            views = 0
            reach = 0
            
            results.append(PostMetrics(
                post_id=post_id,
                post_url=post.get("permalink_url", f"https://facebook.com/{post_id}"),
                platform="facebook",
                created_time=created_time,
                caption=caption,
                views=views,
                interactions=interactions,
                reach=reach,
                follows=0,  # Requires read_insights
                link_clicks=0,  # Requires read_insights
                likes=likes,
                comments=comments_count,
                shares=shares,
            ))
        
        return results
    
    def get_metrics_for_url(self, post_url: str) -> Optional[PostMetrics]:
        """
        Fetch metrics for a specific post by its URL.
        
        Args:
            post_url: The Facebook post URL
            
        Returns:
            PostMetrics object or None if not found
        """
        # Extract post ID from URL
        # URLs can be like:
        # - https://www.facebook.com/{page}/posts/{post_id}
        # - https://www.facebook.com/{page_id}/posts/{post_id}
        # - https://fb.watch/{video_id}
        
        import re
        
        # Try to find post ID in URL
        patterns = [
            r"/posts/(\d+)",
            r"story_fbid=(\d+)",
            r"/videos/(\d+)",
            r"fbid=(\d+)",
        ]
        
        post_id = None
        for pattern in patterns:
            match = re.search(pattern, post_url)
            if match:
                post_id = f"{self.page_id}_{match.group(1)}"
                break
        
        if not post_id:
            return None
        
        try:
            # Get post data
            post_data = self._make_request(
                post_id,
                params={"fields": "id,message,created_time,permalink_url"}
            )
            
            created_time = date_parser.parse(post_data["created_time"]).astimezone(BANGKOK_TZ)
            caption = post_data.get("message", "")
            
            metrics = self.get_post_insights(post_id)
            
            return PostMetrics(
                post_id=post_id,
                post_url=post_data.get("permalink_url", post_url),
                platform="facebook",
                created_time=created_time,
                caption=caption,
                views=metrics["views"],
                interactions=metrics["interactions"],
                reach=metrics["reach"],
                follows=metrics["follows"],
                link_clicks=metrics["link_clicks"],
                likes=metrics["likes"],
                comments=metrics["comments"],
                shares=metrics["shares"],
            )
        except requests.HTTPError:
            return None

