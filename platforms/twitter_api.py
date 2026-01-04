"""
X (Twitter) API client for fetching tweet analytics.
Uses Twitter API v2.
"""

import tweepy
from datetime import datetime, timedelta
from typing import Optional
import re
from dateutil import parser as date_parser

from .facebook_api import PostMetrics


class TwitterAPI:
    """Client for X (Twitter) API v2 to fetch tweet analytics."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
        bearer_token: str,
        user_id: Optional[str] = None
    ):
        """
        Initialize Twitter API client.
        
        Args:
            api_key: Twitter API key
            api_secret: Twitter API secret
            access_token: OAuth 1.0a access token
            access_secret: OAuth 1.0a access token secret
            bearer_token: Bearer token for API v2
            user_id: Twitter user ID (optional, will be fetched if not provided)
        """
        self.bearer_token = bearer_token
        self.user_id = user_id
        
        # Initialize Tweepy client for API v2
        self.client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
            wait_on_rate_limit=True
        )
        
        # Get user ID if not provided
        if not self.user_id:
            self._fetch_user_id()
    
    def _fetch_user_id(self):
        """Fetch the authenticated user's ID."""
        try:
            me = self.client.get_me()
            if me.data:
                self.user_id = me.data.id
        except tweepy.TweepyException as e:
            print(f"Warning: Could not fetch user ID: {e}")
    
    def get_user_tweets(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Fetch tweets from the authenticated user.
        
        Args:
            since: Only fetch tweets created after this datetime
            limit: Maximum number of tweets to fetch
            
        Returns:
            List of tweet data dictionaries
        """
        if not self.user_id:
            raise ValueError("User ID not set. Cannot fetch tweets.")
        
        tweets = []
        pagination_token = None
        
        # Twitter API v2 requires specific fields to be requested
        tweet_fields = [
            "id", "text", "created_at", "public_metrics",
            "non_public_metrics", "organic_metrics"
        ]
        
        while len(tweets) < limit:
            try:
                response = self.client.get_users_tweets(
                    id=self.user_id,
                    start_time=since.isoformat() if since else None,
                    max_results=min(100, limit - len(tweets)),
                    tweet_fields=tweet_fields,
                    pagination_token=pagination_token
                )
                
                if response.data:
                    for tweet in response.data:
                        tweet_data = {
                            "id": tweet.id,
                            "text": tweet.text,
                            "created_at": tweet.created_at,
                            "public_metrics": tweet.public_metrics or {},
                        }
                        
                        # Non-public and organic metrics require elevated access
                        if hasattr(tweet, "non_public_metrics") and tweet.non_public_metrics:
                            tweet_data["non_public_metrics"] = tweet.non_public_metrics
                        if hasattr(tweet, "organic_metrics") and tweet.organic_metrics:
                            tweet_data["organic_metrics"] = tweet.organic_metrics
                        
                        tweets.append(tweet_data)
                
                # Handle pagination
                if response.meta and "next_token" in response.meta:
                    pagination_token = response.meta["next_token"]
                else:
                    break
                    
            except tweepy.TweepyException as e:
                print(f"Error fetching tweets: {e}")
                break
        
        return tweets[:limit]
    
    def get_tweet_metrics(self, tweet_id: str) -> dict:
        """
        Fetch detailed metrics for a specific tweet.
        
        Args:
            tweet_id: The tweet ID
            
        Returns:
            Dictionary with engagement and reach metrics
        """
        try:
            response = self.client.get_tweet(
                id=tweet_id,
                tweet_fields=[
                    "public_metrics",
                    "non_public_metrics",
                    "organic_metrics",
                    "created_at"
                ]
            )
            
            if not response.data:
                return {}
            
            tweet = response.data
            public = tweet.public_metrics or {}
            
            # Non-public metrics (impressions) require elevated access
            non_public = {}
            if hasattr(tweet, "non_public_metrics") and tweet.non_public_metrics:
                non_public = tweet.non_public_metrics
            
            return {
                "likes": public.get("like_count", 0),
                "retweets": public.get("retweet_count", 0),
                "replies": public.get("reply_count", 0),
                "quotes": public.get("quote_count", 0),
                "impressions": non_public.get("impression_count", 0),
                "engagement": (
                    public.get("like_count", 0) +
                    public.get("retweet_count", 0) +
                    public.get("reply_count", 0) +
                    public.get("quote_count", 0)
                ),
                "created_at": tweet.created_at,
            }
            
        except tweepy.TweepyException as e:
            print(f"Error fetching tweet metrics: {e}")
            return {}
    
    def get_posts_with_metrics(
        self,
        days: int = 7,
        since: Optional[datetime] = None
    ) -> list[PostMetrics]:
        """
        Fetch all tweets with their metrics for the specified time period.
        
        Args:
            days: Number of days to look back (ignored if since is provided)
            since: Fetch tweets created after this datetime
            
        Returns:
            List of PostMetrics objects
        """
        if since is None:
            since = datetime.now() - timedelta(days=days)
        
        # Ensure timezone-aware datetime for Twitter API
        if since.tzinfo is None:
            since = since.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        tweets = self.get_user_tweets(since=since)
        results = []
        
        for tweet in tweets:
            tweet_id = str(tweet["id"])
            public_metrics = tweet.get("public_metrics", {})
            non_public = tweet.get("non_public_metrics", {})
            
            created_at = tweet.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            # Calculate engagement
            likes = public_metrics.get("like_count", 0)
            retweets = public_metrics.get("retweet_count", 0)
            replies = public_metrics.get("reply_count", 0)
            quotes = public_metrics.get("quote_count", 0)
            
            engagement = likes + retweets + replies + quotes
            impressions = non_public.get("impression_count", 0)
            
            results.append(PostMetrics(
                post_id=tweet_id,
                post_url=f"https://twitter.com/i/web/status/{tweet_id}",
                platform="twitter",
                created_time=created_at,
                engagement=engagement,
                reach=impressions,  # Twitter uses impressions as reach
                likes=likes,
                comments=replies,
                shares=retweets + quotes,
                impressions=impressions,
            ))
        
        return results
    
    def get_metrics_for_url(self, post_url: str) -> Optional[PostMetrics]:
        """
        Fetch metrics for a specific tweet by its URL.
        
        Args:
            post_url: The Twitter/X post URL
            
        Returns:
            PostMetrics object or None if not found
        """
        # Extract tweet ID from URL
        # URLs can be like:
        # - https://twitter.com/{username}/status/{tweet_id}
        # - https://x.com/{username}/status/{tweet_id}
        
        match = re.search(r"/status/(\d+)", post_url)
        if not match:
            return None
        
        tweet_id = match.group(1)
        
        try:
            metrics = self.get_tweet_metrics(tweet_id)
            
            if not metrics:
                return None
            
            created_at = metrics.get("created_at")
            if isinstance(created_at, str):
                created_at = date_parser.parse(created_at)
            
            return PostMetrics(
                post_id=tweet_id,
                post_url=f"https://twitter.com/i/web/status/{tweet_id}",
                platform="twitter",
                created_time=created_at or datetime.now(),
                engagement=metrics.get("engagement", 0),
                reach=metrics.get("impressions", 0),
                likes=metrics.get("likes", 0),
                comments=metrics.get("replies", 0),
                shares=metrics.get("retweets", 0) + metrics.get("quotes", 0),
                impressions=metrics.get("impressions", 0),
            )
            
        except Exception as e:
            print(f"Error fetching metrics for URL {post_url}: {e}")
            return None

