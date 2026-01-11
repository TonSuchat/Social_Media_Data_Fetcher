"""
Instagram Graph API client for fetching business account post analytics.
Note: Requires Instagram Business or Creator account connected to a Facebook Page.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional
import re
from dateutil import parser as date_parser
import pytz

from .facebook_api import PostMetrics

# Bangkok timezone (GMT+7)
BANGKOK_TZ = pytz.timezone('Asia/Bangkok')


class InstagramAPI:
    """Client for Instagram Graph API to fetch business account post analytics."""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token: str, instagram_account_id: str):
        """
        Initialize Instagram API client.
        
        Args:
            access_token: Page Access Token with instagram_basic, instagram_manage_insights permissions
            instagram_account_id: Instagram Business Account ID (not username!)
        """
        self.access_token = access_token
        self.account_id = instagram_account_id
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make authenticated request to Graph API."""
        params = params or {}
        params["access_token"] = self.access_token
        
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_media_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[dict]:
        """
        Fetch media posts from the Instagram account.
        
        Args:
            since: Only fetch posts created after this datetime
            limit: Maximum number of posts to fetch
            
        Returns:
            List of media data dictionaries
        """
        params = {
            "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
            "limit": min(limit, 50),  # Instagram API max is 50 per request
        }
        
        posts = []
        endpoint = f"{self.account_id}/media"
        
        while len(posts) < limit:
            data = self._make_request(endpoint, params)
            
            for post in data.get("data", []):
                post_time = date_parser.parse(post["timestamp"])
                
                # Filter by date if specified
                if since and post_time < since.replace(tzinfo=post_time.tzinfo):
                    # Posts are returned in reverse chronological order
                    # So if we hit a post older than 'since', we can stop
                    return posts[:limit]
                
                posts.append(post)
            
            # Handle pagination
            paging = data.get("paging", {})
            if "next" in paging and len(posts) < limit:
                cursors = paging.get("cursors", {})
                params["after"] = cursors.get("after")
                if not params.get("after"):
                    break
            else:
                break
        
        return posts[:limit]
    
    def get_media_insights(self, media_id: str, media_type: str = "IMAGE") -> dict:
        """
        Fetch insights/analytics for a specific media post.
        
        Args:
            media_id: The Instagram media ID
            media_type: Type of media (IMAGE, VIDEO, CAROUSEL_ALBUM, REELS)
            
        Returns:
            Dictionary with engagement and reach metrics
        """
        # Different media types support different metrics
        # For images/carousels: impressions, reach, engagement
        # For videos/reels: impressions, reach, video_views, saved
        
        if media_type in ["VIDEO", "REELS"]:
            metrics = "impressions,reach,saved,video_views"
        else:
            metrics = "impressions,reach,saved"
        
        try:
            insights_data = self._make_request(
                f"{media_id}/insights",
                params={"metric": metrics}
            )
            
            insights = {}
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                values = item.get("values", [{}])
                insights[metric_name] = values[0].get("value", 0) if values else 0
            
            return {
                "reach": insights.get("reach", 0),
                "impressions": insights.get("impressions", 0),
                "saved": insights.get("saved", 0),
                "video_views": insights.get("video_views", 0),
            }
            
        except requests.HTTPError:
            # Insights require 'instagram_manage_insights' permission (needs App Review)
            # Silently return zeros - basic engagement (likes/comments) still works
            return {
                "reach": 0,
                "impressions": 0,
                "saved": 0,
                "video_views": 0,
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
        
        posts = self.get_media_posts(since=since)
        results = []
        
        for post in posts:
            media_id = post["id"]
            media_type = post.get("media_type", "IMAGE")
            
            # Parse timestamp and convert to Bangkok timezone
            created_time = date_parser.parse(post["timestamp"]).astimezone(BANGKOK_TZ)
            caption = post.get("caption", "")
            
            # Get basic engagement from post data
            likes = post.get("like_count", 0)
            comments = post.get("comments_count", 0)
            
            # Get detailed insights (may fail without instagram_manage_insights permission)
            insights = self.get_media_insights(media_id, media_type)
            
            # Total interactions = likes + comments + saves
            interactions = likes + comments + insights.get("saved", 0)
            
            results.append(PostMetrics(
                post_id=media_id,
                post_url=post.get("permalink", f"https://instagram.com/p/{media_id}"),
                platform="instagram",
                created_time=created_time,
                caption=caption,
                views=insights.get("impressions", 0),  # impressions = views
                interactions=interactions,
                reach=insights.get("reach", 0),
                follows=0,  # Not available per-post
                link_clicks=0,  # Not available per-post
                likes=likes,
                comments=comments,
                shares=0,  # Instagram doesn't expose share counts
            ))
        
        return results
    
    def get_metrics_for_url(self, post_url: str) -> Optional[PostMetrics]:
        """
        Fetch metrics for a specific post by its URL.
        
        Note: Instagram API doesn't support looking up posts by URL directly.
        We need to fetch recent posts and match by URL.
        
        Args:
            post_url: The Instagram post URL
            
        Returns:
            PostMetrics object or None if not found
        """
        # Normalize URL
        # URLs can be like:
        # - https://www.instagram.com/p/{shortcode}/
        # - https://www.instagram.com/reel/{shortcode}/
        
        shortcode_match = re.search(r"/(p|reel|tv)/([A-Za-z0-9_-]+)", post_url)
        if not shortcode_match:
            return None
        
        target_shortcode = shortcode_match.group(2)
        
        # Fetch recent posts and find matching one
        # We fetch more posts to increase chance of finding the target
        posts = self.get_media_posts(limit=200)
        
        for post in posts:
            permalink = post.get("permalink", "")
            if target_shortcode in permalink:
                media_id = post["id"]
                media_type = post.get("media_type", "IMAGE")
                
                created_time = date_parser.parse(post["timestamp"]).astimezone(BANGKOK_TZ)
                caption = post.get("caption", "")
                
                likes = post.get("like_count", 0)
                comments = post.get("comments_count", 0)
                
                insights = self.get_media_insights(media_id, media_type)
                interactions = likes + comments + insights.get("saved", 0)
                
                return PostMetrics(
                    post_id=media_id,
                    post_url=permalink,
                    platform="instagram",
                    created_time=created_time,
                    caption=caption,
                    views=insights.get("impressions", 0),
                    interactions=interactions,
                    reach=insights.get("reach", 0),
                    follows=0,
                    link_clicks=0,
                    likes=likes,
                    comments=comments,
                    shares=0,
                )
        
        return None
    
    def get_account_insights(self, period: str = "day", days: int = 7) -> dict:
        """
        Fetch account-level insights (overall performance).
        
        Args:
            period: Time period aggregation (day, week, days_28)
            days: Number of days for the 'day' period
            
        Returns:
            Dictionary with account metrics
        """
        metrics = "impressions,reach,profile_views,follower_count"
        
        try:
            insights_data = self._make_request(
                f"{self.account_id}/insights",
                params={
                    "metric": metrics,
                    "period": period,
                }
            )
            
            insights = {}
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                values = item.get("values", [])
                
                if period == "day" and values:
                    # Sum up daily values
                    total = sum(v.get("value", 0) for v in values[-days:])
                    insights[metric_name] = total
                elif values:
                    insights[metric_name] = values[0].get("value", 0)
            
            return insights
            
        except requests.HTTPError as e:
            print(f"Warning: Could not fetch account insights: {e}")
            return {}

