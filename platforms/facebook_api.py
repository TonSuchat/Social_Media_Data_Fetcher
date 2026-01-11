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
    
    BASE_URL = "https://graph.facebook.com/v24.0"
    
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
    
    def get_post_insights(self, post_id: str) -> dict:
        """
        Fetch engagement metrics for a specific post using Graph API v24.0.
        
        Requires 'read_insights' permission.
        
        Metrics used:
        - post_impressions: Total views
        - post_impressions_unique: Reach (unique viewers)  
        - post_clicks_by_type: Link clicks breakdown
        - post_reactions_by_type_total: Total reactions (likes, love, etc.)
        
        Note: 'follows' per post is NOT available - page_fan_adds is page-level only.
        
        Args:
            post_id: The Facebook post ID (format: {page_id}_{post_id})
            
        Returns:
            Dictionary with engagement metrics
        """
        # Initialize defaults
        reactions = 0
        comments = 0
        shares = 0
        views = 0
        reach = 0
        follows = 0  # Not available per-post in Facebook API
        link_clicks = 0
        
        # Extract just the post ID part (after underscore)
        # Sometimes need to query with just post ID, sometimes with full ID
        post_id_only = post_id.split("_")[-1] if "_" in post_id else post_id
        
        # Fetch insights using valid metrics for API v24.0
        # Metrics:
        #   - post_media_view: Views
        #   - post_impressions_unique: Reach (unique viewers)
        #   - post_clicks_by_type: Click breakdown (link clicks, photo view, etc.)
        #   - post_reactions_by_type_total: Reactions breakdown (like, love, haha, etc.)
        #   - post_activity_by_action_type: Engagement breakdown (like, comment, share)
        try:
            insights_data = self._make_request(
                f"{post_id}/insights",
                params={
                    "metric": "post_media_view,post_impressions_unique,post_clicks_by_type,post_reactions_by_type_total,post_activity_by_action_type"
                }
            )
            
            if self.debug:
                print(f"\n🔍 DEBUG - Insights for {post_id}:")
                print(f"   Raw insights: {insights_data}")
            
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                values = item.get("values", [{}])
                value = values[0].get("value", 0) if values else 0
                
                if metric_name == "post_media_view":
                    views = value if isinstance(value, int) else 0
                elif metric_name == "post_impressions_unique":
                    reach = value if isinstance(value, int) else 0
                elif metric_name == "post_clicks_by_type":
                    # value is a dict like {"link clicks": 5, "other clicks": 10, "photo view": 4}
                    if isinstance(value, dict):
                        link_clicks = value.get("link clicks", 0)
                        if self.debug:
                            print(f"   post_clicks_by_type: {value}")
                elif metric_name == "post_reactions_by_type_total":
                    # value is a dict like {"like": 50, "love": 10, "haha": 5, ...}
                    if isinstance(value, dict):
                        reactions = sum(value.values())
                        if self.debug:
                            print(f"   post_reactions_by_type_total: {value}")
                    else:
                        reactions = value if isinstance(value, int) else 0
                elif metric_name == "post_activity_by_action_type":
                    # value is a dict like {"like": 49, "comment": 1, "share": 15}
                    # This gives us comments and shares without needing pages_read_engagement!
                    if isinstance(value, dict):
                        comments = value.get("comment", 0)
                        shares = value.get("share", 0)
                        if self.debug:
                            print(f"   post_activity_by_action_type: {value}")
                        
        except requests.HTTPError as e:
            if self.debug:
                try:
                    error_detail = e.response.json() if e.response else {}
                    print(f"\n🔍 DEBUG - Insights error for {post_id}: {error_detail}")
                except:
                    print(f"\n🔍 DEBUG - Insights error for {post_id}: {e}")
        
        # Interactions = total engagement (reactions + comments + shares + link clicks)
        interactions = reactions + comments + shares + link_clicks
        
        return {
            "likes": reactions,  # "likes" field now holds total reactions
            "comments": comments,
            "shares": shares,
            "views": views,
            "reach": reach,
            "follows": follows,
            "link_clicks": link_clicks,
            "interactions": interactions,
        }
    
    def get_posts_with_metrics(
        self,
        days: int = 7,
        since: Optional[datetime] = None
    ) -> list[PostMetrics]:
        """
        Fetch all posts with their metrics for the specified time period.
        
        Uses read_insights permission to fetch:
        - Views (post_impressions)
        - Reach (post_impressions_unique)
        - Link clicks (from post_clicks_by_type)
        - Reactions (from post_reactions_by_type_total)
        - Comments & Shares (from post object)
        
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
            
            # Fetch all insights metrics (views, reach, reactions, link clicks, comments, shares)
            # post_activity_by_action_type provides comments and shares!
            metrics = self.get_post_insights(post_id)
            
            # Fallback: use shares from post data if insights didn't return it
            if metrics["shares"] == 0:
                metrics["shares"] = post.get("shares", {}).get("count", 0)
            
            if self.debug:
                print(f"\n🔍 DEBUG - Post {post_id} metrics: {metrics}")
            
            results.append(PostMetrics(
                post_id=post_id,
                post_url=post.get("permalink_url", f"https://facebook.com/{post_id}"),
                platform="facebook",
                created_time=created_time,
                caption=caption,
                views=metrics["views"],
                interactions=metrics["interactions"],
                reach=metrics["reach"],
                follows=metrics["follows"],  # Not available per-post
                link_clicks=metrics["link_clicks"],
                likes=metrics["likes"],  # Total reactions
                comments=metrics["comments"],  # Requires pages_read_engagement
                shares=metrics["shares"],
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
            
            # Fetch all metrics using insights API
            metrics = self.get_post_insights(post_id)
            
            return PostMetrics(
                post_id=post_id,
                post_url=post_data.get("permalink_url", post_url),
                platform="facebook",
                created_time=created_time,
                caption=caption,
                views=metrics["views"],
                interactions=metrics["interactions"],  # reactions + link clicks
                reach=metrics["reach"],
                follows=metrics["follows"],  # Not available per-post
                link_clicks=metrics["link_clicks"],
                likes=metrics["likes"],  # Total reactions
                comments=metrics["comments"],
                shares=metrics["shares"],
            )
        except requests.HTTPError:
            return None

