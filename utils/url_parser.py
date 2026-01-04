"""
URL parser to identify social media platforms from post URLs.
"""

import re
from typing import Optional
from urllib.parse import urlparse


class URLParser:
    """Parse and identify social media post URLs."""
    
    # Platform detection patterns
    PLATFORM_PATTERNS = {
        "facebook": [
            r"facebook\.com",
            r"fb\.com",
            r"fb\.watch",
            r"fb\.me",
        ],
        "instagram": [
            r"instagram\.com",
            r"instagr\.am",
        ],
        "twitter": [
            r"twitter\.com",
            r"x\.com",
            r"t\.co",
        ],
        "tiktok": [
            r"tiktok\.com",
            r"vm\.tiktok\.com",
        ],
        "youtube": [
            r"youtube\.com",
            r"youtu\.be",
        ],
        "linkedin": [
            r"linkedin\.com",
        ],
    }
    
    @classmethod
    def detect_platform(cls, url: str) -> Optional[str]:
        """
        Detect the social media platform from a URL.
        
        Args:
            url: The post URL
            
        Returns:
            Platform name (lowercase) or None if not recognized
        """
        url_lower = url.lower()
        
        for platform, patterns in cls.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return platform
        
        return None
    
    @classmethod
    def extract_post_id(cls, url: str, platform: Optional[str] = None) -> Optional[str]:
        """
        Extract the post/content ID from a URL.
        
        Args:
            url: The post URL
            platform: Optional platform hint (auto-detected if not provided)
            
        Returns:
            Post ID string or None if not found
        """
        if platform is None:
            platform = cls.detect_platform(url)
        
        if platform == "facebook":
            return cls._extract_facebook_id(url)
        elif platform == "instagram":
            return cls._extract_instagram_id(url)
        elif platform == "twitter":
            return cls._extract_twitter_id(url)
        elif platform == "tiktok":
            return cls._extract_tiktok_id(url)
        elif platform == "youtube":
            return cls._extract_youtube_id(url)
        
        return None
    
    @classmethod
    def _extract_facebook_id(cls, url: str) -> Optional[str]:
        """Extract post ID from Facebook URL."""
        patterns = [
            r"/posts/(\d+)",
            r"/videos/(\d+)",
            r"story_fbid=(\d+)",
            r"fbid=(\d+)",
            r"/permalink/(\d+)",
            r"/photos/[^/]+/(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @classmethod
    def _extract_instagram_id(cls, url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL."""
        patterns = [
            r"/(p|reel|tv)/([A-Za-z0-9_-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(2)
        
        return None
    
    @classmethod
    def _extract_twitter_id(cls, url: str) -> Optional[str]:
        """Extract tweet ID from Twitter/X URL."""
        patterns = [
            r"/status/(\d+)",
            r"/statuses/(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @classmethod
    def _extract_tiktok_id(cls, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL."""
        patterns = [
            r"/video/(\d+)",
            r"vm\.tiktok\.com/([A-Za-z0-9]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @classmethod
    def _extract_youtube_id(cls, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r"v=([A-Za-z0-9_-]{11})",
            r"youtu\.be/([A-Za-z0-9_-]{11})",
            r"/embed/([A-Za-z0-9_-]{11})",
            r"/shorts/([A-Za-z0-9_-]{11})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @classmethod
    def normalize_url(cls, url: str) -> str:
        """
        Normalize a URL for comparison purposes.
        
        Args:
            url: The URL to normalize
            
        Returns:
            Normalized URL string
        """
        url = url.strip().lower()
        
        # Parse URL
        parsed = urlparse(url)
        
        # Remove www. prefix
        host = parsed.netloc.replace("www.", "")
        
        # Normalize x.com to twitter.com
        if host == "x.com":
            host = "twitter.com"
        
        # Remove trailing slashes from path
        path = parsed.path.rstrip("/")
        
        # Reconstruct URL without query params or fragments
        return f"{parsed.scheme}://{host}{path}"
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Check if a URL is a valid social media post URL.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        platform = cls.detect_platform(url)
        if not platform:
            return False
        
        post_id = cls.extract_post_id(url, platform)
        return post_id is not None
    
    @classmethod
    def get_canonical_url(cls, url: str) -> Optional[str]:
        """
        Convert a URL to its canonical form.
        
        Args:
            url: The post URL
            
        Returns:
            Canonical URL or None if not recognized
        """
        platform = cls.detect_platform(url)
        post_id = cls.extract_post_id(url, platform)
        
        if not platform or not post_id:
            return None
        
        canonical_formats = {
            "facebook": f"https://www.facebook.com/permalink.php?story_fbid={post_id}",
            "instagram": f"https://www.instagram.com/p/{post_id}/",
            "twitter": f"https://twitter.com/i/web/status/{post_id}",
            "tiktok": f"https://www.tiktok.com/video/{post_id}",
            "youtube": f"https://www.youtube.com/watch?v={post_id}",
        }
        
        return canonical_formats.get(platform)

