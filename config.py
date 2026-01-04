"""
Configuration loader for Social Media Report Generator.
Loads settings from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


@dataclass
class MetaConfig:
    """Configuration for Meta (Facebook & Instagram) APIs."""
    access_token: str
    facebook_page_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    
    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)
    
    @property
    def facebook_enabled(self) -> bool:
        return bool(self.access_token and self.facebook_page_id)
    
    @property
    def instagram_enabled(self) -> bool:
        return bool(self.access_token and self.instagram_account_id)


@dataclass
class TwitterConfig:
    """Configuration for X (Twitter) API."""
    api_key: str
    api_secret: str
    access_token: str
    access_secret: str
    bearer_token: str
    user_id: Optional[str] = None
    
    @property
    def is_configured(self) -> bool:
        return all([
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_secret,
            self.bearer_token
        ])


@dataclass
class GoogleSheetsConfig:
    """Configuration for Google Sheets API."""
    sheet_id: str
    credentials_path: str
    sheet_name: str = "Sheet1"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.sheet_id and self.credentials_path)


@dataclass
class AppConfig:
    """Main application configuration."""
    meta: MetaConfig
    twitter: TwitterConfig
    google_sheets: GoogleSheetsConfig
    default_days_lookback: int = 7
    
    def get_enabled_platforms(self) -> list[str]:
        """Returns list of configured and enabled platforms."""
        platforms = []
        if self.meta.facebook_enabled:
            platforms.append("facebook")
        if self.meta.instagram_enabled:
            platforms.append("instagram")
        if self.twitter.is_configured:
            platforms.append("twitter")
        return platforms


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    
    meta_config = MetaConfig(
        access_token=os.getenv("META_ACCESS_TOKEN", ""),
        facebook_page_id=os.getenv("FACEBOOK_PAGE_ID"),
        instagram_account_id=os.getenv("INSTAGRAM_ACCOUNT_ID"),
    )
    
    twitter_config = TwitterConfig(
        api_key=os.getenv("TWITTER_API_KEY", ""),
        api_secret=os.getenv("TWITTER_API_SECRET", ""),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN", ""),
        access_secret=os.getenv("TWITTER_ACCESS_SECRET", ""),
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN", ""),
        user_id=os.getenv("TWITTER_USER_ID"),
    )
    
    google_config = GoogleSheetsConfig(
        sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_service_account.json"),
        sheet_name=os.getenv("GOOGLE_SHEET_NAME", "Sheet1"),
    )
    
    return AppConfig(
        meta=meta_config,
        twitter=twitter_config,
        google_sheets=google_config,
        default_days_lookback=int(os.getenv("DEFAULT_DAYS_LOOKBACK", "7")),
    )


# Global config instance
config = load_config()

