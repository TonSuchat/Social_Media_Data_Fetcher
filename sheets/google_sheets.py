"""
Google Sheets client for reading and updating social media tracking spreadsheet.
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from platforms.facebook_api import PostMetrics


# Google Sheets API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


@dataclass
class SheetRow:
    """Represents a row in the tracking spreadsheet."""
    row_number: int
    date: str
    time: str
    platform: str
    post_url: str
    caption: str = ""
    views: int = 0
    interactions: int = 0
    reach: int = 0
    follows: int = 0
    link_clicks: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class GoogleSheetsClient:
    """Client for reading and updating Google Sheets."""
    
    # Expected column headers (order matters for column indices)
    EXPECTED_HEADERS = [
        "Date", "Time", "Platform", "Post URL", "Caption",
        "Views", "Interactions", "Reach", "Follows", "Link Clicks",
        "Likes", "Comments", "Shares"
    ]
    
    # Column indices (0-based)
    COL_DATE = 0
    COL_TIME = 1
    COL_PLATFORM = 2
    COL_URL = 3
    COL_CAPTION = 4
    COL_VIEWS = 5
    COL_INTERACTIONS = 6
    COL_REACH = 7
    COL_FOLLOWS = 8
    COL_LINK_CLICKS = 9
    COL_LIKES = 10
    COL_COMMENTS = 11
    COL_SHARES = 12
    
    def __init__(self, credentials_path: str, spreadsheet_id: str, sheet_name: str = "Sheet1"):
        """
        Initialize Google Sheets client.
        
        Args:
            credentials_path: Path to service account JSON credentials file
            spreadsheet_id: The spreadsheet ID from the Google Sheets URL
            sheet_name: Name of the sheet/tab to use
        """
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        
        self._client: Optional[gspread.Client] = None
        self._sheet: Optional[gspread.Worksheet] = None
    
    def _connect(self):
        """Establish connection to Google Sheets."""
        if self._client is None:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )
            self._client = gspread.authorize(credentials)
        
        if self._sheet is None:
            spreadsheet = self._client.open_by_key(self.spreadsheet_id)
            self._sheet = spreadsheet.worksheet(self.sheet_name)
    
    @property
    def sheet(self) -> gspread.Worksheet:
        """Get the connected worksheet."""
        self._connect()
        return self._sheet
    
    def ensure_headers(self):
        """Ensure the sheet has the expected headers."""
        self._connect()
        
        # Check first row for headers
        first_row = self._sheet.row_values(1)
        
        if not first_row or first_row != self.EXPECTED_HEADERS:
            # Set headers (A1 to M1 for 13 columns)
            self._sheet.update("A1:M1", [self.EXPECTED_HEADERS])
            print(f"Headers set: {self.EXPECTED_HEADERS}")
    
    def get_all_rows(self) -> list[SheetRow]:
        """
        Fetch all data rows from the sheet.
        
        Returns:
            List of SheetRow objects (excludes header row)
        """
        self._connect()
        
        all_values = self._sheet.get_all_values()
        
        if len(all_values) <= 1:  # Only header or empty
            return []
        
        def safe_int(val):
            """Convert to int, handling empty strings and commas."""
            if not val:
                return 0
            try:
                return int(str(val).replace(",", ""))
            except ValueError:
                return 0
        
        rows = []
        for i, row in enumerate(all_values[1:], start=2):  # Skip header, row numbers start at 2
            if len(row) >= 4 and row[self.COL_URL]:  # Must have at least URL
                rows.append(SheetRow(
                    row_number=i,
                    date=row[self.COL_DATE] if len(row) > self.COL_DATE else "",
                    time=row[self.COL_TIME] if len(row) > self.COL_TIME else "",
                    platform=row[self.COL_PLATFORM] if len(row) > self.COL_PLATFORM else "",
                    post_url=row[self.COL_URL] if len(row) > self.COL_URL else "",
                    caption=row[self.COL_CAPTION] if len(row) > self.COL_CAPTION else "",
                    views=safe_int(row[self.COL_VIEWS]) if len(row) > self.COL_VIEWS else 0,
                    interactions=safe_int(row[self.COL_INTERACTIONS]) if len(row) > self.COL_INTERACTIONS else 0,
                    reach=safe_int(row[self.COL_REACH]) if len(row) > self.COL_REACH else 0,
                    follows=safe_int(row[self.COL_FOLLOWS]) if len(row) > self.COL_FOLLOWS else 0,
                    link_clicks=safe_int(row[self.COL_LINK_CLICKS]) if len(row) > self.COL_LINK_CLICKS else 0,
                    likes=safe_int(row[self.COL_LIKES]) if len(row) > self.COL_LIKES else 0,
                    comments=safe_int(row[self.COL_COMMENTS]) if len(row) > self.COL_COMMENTS else 0,
                    shares=safe_int(row[self.COL_SHARES]) if len(row) > self.COL_SHARES else 0,
                ))
        
        return rows
    
    def find_row_by_url(self, post_url: str) -> Optional[SheetRow]:
        """
        Find a row by post URL.
        
        Args:
            post_url: The post URL to search for
            
        Returns:
            SheetRow if found, None otherwise
        """
        rows = self.get_all_rows()
        
        # Normalize URLs for comparison
        normalized_target = self._normalize_url(post_url)
        
        for row in rows:
            if self._normalize_url(row.post_url) == normalized_target:
                return row
        
        return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        url = url.lower().strip()
        # Remove trailing slashes
        url = url.rstrip("/")
        # Remove www.
        url = url.replace("www.", "")
        # Normalize x.com to twitter.com
        url = url.replace("x.com/", "twitter.com/")
        return url
    
    def update_row_metrics(self, row_number: int, metrics: 'PostMetrics'):
        """
        Update all metrics for a specific row.
        
        Args:
            row_number: The row number to update (1-based)
            metrics: PostMetrics object with new values
        """
        self._connect()
        
        # Update columns F through M (Views, Interactions, Reach, Follows, Link Clicks, Likes, Comments, Shares)
        values = [
            metrics.views,
            metrics.interactions,
            metrics.reach,
            metrics.follows,
            metrics.link_clicks,
            metrics.likes,
            metrics.comments,
            metrics.shares,
        ]
        self._sheet.update(f"F{row_number}:M{row_number}", [values])
    
    def add_post(self, metrics: PostMetrics) -> int:
        """
        Add a new post to the sheet.
        
        Args:
            metrics: PostMetrics object with post data
            
        Returns:
            Row number of the new row
        """
        self._connect()
        
        # Truncate caption if too long (to fit in cell nicely)
        caption = metrics.caption[:200] + "..." if len(metrics.caption) > 200 else metrics.caption
        caption = caption.replace("\n", " ")  # Remove newlines for cleaner display
        
        new_row = [
            metrics.created_time.strftime("%Y-%m-%d"),
            metrics.created_time.strftime("%H:%M"),
            metrics.platform.capitalize(),
            metrics.post_url,
            caption,
            metrics.views,
            metrics.interactions,
            metrics.reach,
            metrics.follows,
            metrics.link_clicks,
            metrics.likes,
            metrics.comments,
            metrics.shares,
        ]
        
        self._sheet.append_row(new_row)
        
        # Return the new row number
        return len(self._sheet.get_all_values())
    
    def update_or_add_post(self, metrics: PostMetrics) -> tuple[str, int]:
        """
        Update existing post metrics or add new post if not found.
        
        Args:
            metrics: PostMetrics object with post data
            
        Returns:
            Tuple of (action, row_number) where action is 'updated' or 'added'
        """
        existing_row = self.find_row_by_url(metrics.post_url)
        
        if existing_row:
            self.update_row_metrics(existing_row.row_number, metrics)
            return ("updated", existing_row.row_number)
        else:
            row_number = self.add_post(metrics)
            return ("added", row_number)
    
    def batch_update_metrics(self, metrics_list: list[PostMetrics], dry_run: bool = False) -> dict:
        """
        Update multiple posts at once.
        
        Args:
            metrics_list: List of PostMetrics objects
            dry_run: If True, don't actually update, just report what would happen
            
        Returns:
            Summary dictionary with counts of updates and additions
        """
        summary = {
            "updated": 0,
            "added": 0,
            "skipped": 0,
            "details": [],
        }
        
        for metrics in metrics_list:
            existing_row = self.find_row_by_url(metrics.post_url)
            
            if existing_row:
                if dry_run:
                    summary["details"].append({
                        "action": "would_update",
                        "url": metrics.post_url,
                        "row": existing_row.row_number,
                        "old_views": existing_row.views,
                        "new_views": metrics.views,
                        "old_interactions": existing_row.interactions,
                        "new_interactions": metrics.interactions,
                        "old_reach": existing_row.reach,
                        "new_reach": metrics.reach,
                    })
                else:
                    self.update_row_metrics(existing_row.row_number, metrics)
                    summary["details"].append({
                        "action": "updated",
                        "url": metrics.post_url,
                        "row": existing_row.row_number,
                    })
                summary["updated"] += 1
            else:
                if dry_run:
                    summary["details"].append({
                        "action": "would_add",
                        "url": metrics.post_url,
                        "platform": metrics.platform,
                        "views": metrics.views,
                        "interactions": metrics.interactions,
                        "reach": metrics.reach,
                    })
                else:
                    row_number = self.add_post(metrics)
                    summary["details"].append({
                        "action": "added",
                        "url": metrics.post_url,
                        "row": row_number,
                    })
                summary["added"] += 1
        
        return summary
    
    def get_posts_needing_update(self, days_old: int = 7) -> list[SheetRow]:
        """
        Get posts that are due for a metrics update.
        
        Args:
            days_old: Only return posts older than this many days
            
        Returns:
            List of SheetRow objects that need updating
        """
        rows = self.get_all_rows()
        cutoff_date = datetime.now().date()
        
        posts_to_update = []
        for row in rows:
            if row.date:
                try:
                    post_date = datetime.strptime(row.date, "%Y-%m-%d").date()
                    age_days = (cutoff_date - post_date).days
                    
                    if age_days >= days_old:
                        posts_to_update.append(row)
                except ValueError:
                    # Invalid date format, skip
                    continue
        
        return posts_to_update

