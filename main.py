#!/usr/bin/env python3
"""
Social Media Weekly Report Generator

Automatically fetch engagement and reach metrics from Facebook, Instagram, and X (Twitter),
then update your Google Sheet tracking spreadsheet.

Usage:
    python main.py fetch --days 7
    python main.py update-sheet
    python main.py run
    python main.py run --dry-run
"""

import click
from datetime import datetime, timedelta
from typing import Optional
import sys

from config import config
from platforms.facebook_api import FacebookAPI, PostMetrics
from platforms.instagram_api import InstagramAPI
from platforms.twitter_api import TwitterAPI
from sheets.google_sheets import GoogleSheetsClient
from utils.url_parser import URLParser


def create_facebook_client() -> Optional[FacebookAPI]:
    """Create Facebook API client if configured."""
    if config.meta.facebook_enabled:
        return FacebookAPI(
            access_token=config.meta.access_token,
            page_id=config.meta.facebook_page_id
        )
    return None


def create_instagram_client() -> Optional[InstagramAPI]:
    """Create Instagram API client if configured."""
    if config.meta.instagram_enabled:
        return InstagramAPI(
            access_token=config.meta.access_token,
            instagram_account_id=config.meta.instagram_account_id
        )
    return None


def create_twitter_client() -> Optional[TwitterAPI]:
    """Create Twitter API client if configured."""
    if config.twitter.is_configured:
        return TwitterAPI(
            api_key=config.twitter.api_key,
            api_secret=config.twitter.api_secret,
            access_token=config.twitter.access_token,
            access_secret=config.twitter.access_secret,
            bearer_token=config.twitter.bearer_token,
            user_id=config.twitter.user_id
        )
    return None


def create_sheets_client() -> Optional[GoogleSheetsClient]:
    """Create Google Sheets client if configured."""
    if config.google_sheets.is_configured:
        return GoogleSheetsClient(
            credentials_path=config.google_sheets.credentials_path,
            spreadsheet_id=config.google_sheets.sheet_id,
            sheet_name=config.google_sheets.sheet_name
        )
    return None


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Social Media Weekly Report Generator 📊
    
    Automatically fetch engagement and reach metrics from social media platforms
    and update your Google Sheet tracking spreadsheet.
    """
    pass


@cli.command()
@click.option("--days", default=7, help="Number of days to look back (default: 7)")
@click.option("--since", type=click.DateTime(), help="Fetch posts since this date (overrides --days)")
@click.option("--platform", type=click.Choice(["facebook", "instagram", "twitter", "all"]), 
              default="all", help="Platform to fetch from (default: all)")
@click.option("--debug", is_flag=True, help="Show raw API responses for debugging")
def fetch(days: int, since: Optional[datetime], platform: str, debug: bool):
    """Fetch metrics from social media platforms.
    
    This command fetches engagement and reach data for posts from the specified
    time period and displays the results.
    """
    if since:
        start_date = since
    else:
        start_date = datetime.now() - timedelta(days=days)
    
    click.echo(f"\n📅 Fetching posts since {start_date.strftime('%Y-%m-%d')}")
    click.echo("=" * 60)
    
    all_metrics: list[PostMetrics] = []
    
    # Fetch from Facebook
    if platform in ["facebook", "all"]:
        fb_client = create_facebook_client()
        if fb_client:
            click.echo("\n📘 Fetching from Facebook...")
            try:
                fb_client.debug = debug  # Enable debug mode if requested
                fb_metrics = fb_client.get_posts_with_metrics(since=start_date)
                all_metrics.extend(fb_metrics)
                click.echo(f"   Found {len(fb_metrics)} posts")
            except Exception as e:
                click.echo(f"   ❌ Error: {e}", err=True)
        elif platform == "facebook":
            click.echo("❌ Facebook is not configured. Check your .env file.", err=True)
    
    # Fetch from Instagram
    if platform in ["instagram", "all"]:
        ig_client = create_instagram_client()
        if ig_client:
            click.echo("\n📸 Fetching from Instagram...")
            try:
                ig_metrics = ig_client.get_posts_with_metrics(since=start_date)
                all_metrics.extend(ig_metrics)
                click.echo(f"   Found {len(ig_metrics)} posts")
            except Exception as e:
                click.echo(f"   ❌ Error: {e}", err=True)
        elif platform == "instagram":
            click.echo("❌ Instagram is not configured. Check your .env file.", err=True)
    
    # Fetch from Twitter
    if platform in ["twitter", "all"]:
        tw_client = create_twitter_client()
        if tw_client:
            click.echo("\n🐦 Fetching from X (Twitter)...")
            try:
                tw_metrics = tw_client.get_posts_with_metrics(since=start_date)
                all_metrics.extend(tw_metrics)
                click.echo(f"   Found {len(tw_metrics)} posts")
            except Exception as e:
                click.echo(f"   ❌ Error: {e}", err=True)
        elif platform == "twitter":
            click.echo("❌ Twitter is not configured. Check your .env file.", err=True)
    
    # Display results
    if all_metrics:
        click.echo("\n" + "=" * 60)
        click.echo("📊 RESULTS")
        click.echo("=" * 60)
        
        # Sort by date
        all_metrics.sort(key=lambda m: m.created_time, reverse=True)
        
        for m in all_metrics:
            platform_emoji = {"facebook": "📘", "instagram": "📸", "twitter": "🐦"}.get(m.platform, "📱")
            click.echo(f"\n{platform_emoji} {m.platform.capitalize()}")
            click.echo(f"   🆔 Post ID: {m.post_id}")  # Show post ID for testing
            click.echo(f"   📅 {m.created_time.strftime('%Y-%m-%d %H:%M')} (Bangkok)")
            # Show caption preview (first 60 chars)
            caption_preview = m.caption[:60] + "..." if len(m.caption) > 60 else m.caption
            caption_preview = caption_preview.replace("\n", " ")  # Remove newlines
            if caption_preview:
                click.echo(f"   📝 {caption_preview}")
            click.echo(f"   🔗 {m.post_url}")
            click.echo(f"   🔄 Shares: {m.shares:,}")
            if m.likes > 0 or m.comments > 0:
                click.echo(f"   ❤️ Likes: {m.likes:,} | 💬 Comments: {m.comments:,}")
            if m.views > 0:
                click.echo(f"   👁️ Views: {m.views:,}")
            if m.reach > 0:
                click.echo(f"   👥 Reach: {m.reach:,}")
            if m.follows > 0:
                click.echo(f"   ➕ Follows: {m.follows:,}")
            if m.link_clicks > 0:
                click.echo(f"   🔗 Link Clicks: {m.link_clicks:,}")
        
        click.echo(f"\n✅ Total: {len(all_metrics)} posts fetched")
    else:
        click.echo("\n⚠️ No posts found for the specified time period.")
        enabled = config.get_enabled_platforms()
        if not enabled:
            click.echo("   No platforms are configured. Check your .env file.")


@cli.command("update-sheet")
@click.option("--dry-run", is_flag=True, help="Preview changes without updating")
def update_sheet(dry_run: bool):
    """Update Google Sheet with fresh metrics for existing posts.
    
    This command reads your Google Sheet, finds posts that need updating,
    fetches fresh metrics from the respective platforms, and updates the sheet.
    """
    sheets_client = create_sheets_client()
    if not sheets_client:
        click.echo("❌ Google Sheets is not configured. Check your .env file.", err=True)
        sys.exit(1)
    
    click.echo("\n📋 Reading Google Sheet...")
    
    try:
        sheets_client.ensure_headers()
        rows = sheets_client.get_all_rows()
        click.echo(f"   Found {len(rows)} posts in sheet")
    except Exception as e:
        click.echo(f"❌ Error reading sheet: {e}", err=True)
        sys.exit(1)
    
    if not rows:
        click.echo("⚠️ No posts found in the sheet.")
        return
    
    # Group URLs by platform
    fb_urls = []
    ig_urls = []
    tw_urls = []
    
    for row in rows:
        platform = URLParser.detect_platform(row.post_url)
        if platform == "facebook":
            fb_urls.append((row, row.post_url))
        elif platform == "instagram":
            ig_urls.append((row, row.post_url))
        elif platform == "twitter":
            tw_urls.append((row, row.post_url))
    
    click.echo(f"\n   Facebook posts: {len(fb_urls)}")
    click.echo(f"   Instagram posts: {len(ig_urls)}")
    click.echo(f"   Twitter posts: {len(tw_urls)}")
    
    updates = []
    
    # Fetch Facebook metrics
    if fb_urls:
        fb_client = create_facebook_client()
        if fb_client:
            click.echo("\n📘 Fetching Facebook metrics...")
            for row, url in fb_urls:
                try:
                    metrics = fb_client.get_metrics_for_url(url)
                    if metrics:
                        updates.append((row, metrics))
                        click.echo(f"   ✓ {url[:50]}...")
                    else:
                        click.echo(f"   ⚠️ Could not find: {url[:50]}...")
                except Exception as e:
                    click.echo(f"   ❌ Error: {e}")
    
    # Fetch Instagram metrics
    if ig_urls:
        ig_client = create_instagram_client()
        if ig_client:
            click.echo("\n📸 Fetching Instagram metrics...")
            for row, url in ig_urls:
                try:
                    metrics = ig_client.get_metrics_for_url(url)
                    if metrics:
                        updates.append((row, metrics))
                        click.echo(f"   ✓ {url[:50]}...")
                    else:
                        click.echo(f"   ⚠️ Could not find: {url[:50]}...")
                except Exception as e:
                    click.echo(f"   ❌ Error: {e}")
    
    # Fetch Twitter metrics
    if tw_urls:
        tw_client = create_twitter_client()
        if tw_client:
            click.echo("\n🐦 Fetching Twitter metrics...")
            for row, url in tw_urls:
                try:
                    metrics = tw_client.get_metrics_for_url(url)
                    if metrics:
                        updates.append((row, metrics))
                        click.echo(f"   ✓ {url[:50]}...")
                    else:
                        click.echo(f"   ⚠️ Could not find: {url[:50]}...")
                except Exception as e:
                    click.echo(f"   ❌ Error: {e}")
    
    # Apply updates
    if updates:
        click.echo("\n" + "=" * 60)
        
        if dry_run:
            click.echo("🔍 DRY RUN - Changes that would be made:")
            for row, metrics in updates:
                click.echo(f"\n   Row {row.row_number}: {row.post_url[:40]}...")
                click.echo(f"      Views: {row.views:,} → {metrics.views:,}")
                click.echo(f"      Interactions: {row.interactions:,} → {metrics.interactions:,}")
                click.echo(f"      Reach: {row.reach:,} → {metrics.reach:,}")
        else:
            click.echo("📝 Updating sheet...")
            for row, metrics in updates:
                try:
                    sheets_client.update_row_metrics(row.row_number, metrics)
                    click.echo(f"   ✓ Updated row {row.row_number}")
                except Exception as e:
                    click.echo(f"   ❌ Error updating row {row.row_number}: {e}")
        
        click.echo(f"\n✅ {'Would update' if dry_run else 'Updated'} {len(updates)} posts")
    else:
        click.echo("\n⚠️ No posts could be updated.")


@cli.command()
@click.option("--days", default=7, help="Number of days to look back (default: 7)")
@click.option("--dry-run", is_flag=True, help="Preview changes without updating")
def run(days: int, dry_run: bool):
    """Fetch new posts and update the Google Sheet.
    
    This is the main command that does everything:
    1. Fetches recent posts from all configured platforms
    2. Adds new posts to the Google Sheet
    3. Updates metrics for existing posts
    """
    sheets_client = create_sheets_client()
    if not sheets_client:
        click.echo("❌ Google Sheets is not configured. Check your .env file.", err=True)
        sys.exit(1)
    
    start_date = datetime.now() - timedelta(days=days)
    
    click.echo(f"\n🚀 Running weekly report update")
    click.echo(f"📅 Looking back {days} days (since {start_date.strftime('%Y-%m-%d')})")
    click.echo("=" * 60)
    
    # Ensure sheet has headers
    sheets_client.ensure_headers()
    
    all_metrics: list[PostMetrics] = []
    
    # Fetch from all platforms
    fb_client = create_facebook_client()
    if fb_client:
        click.echo("\n📘 Fetching from Facebook...")
        try:
            metrics = fb_client.get_posts_with_metrics(since=start_date)
            all_metrics.extend(metrics)
            click.echo(f"   Found {len(metrics)} posts")
        except Exception as e:
            click.echo(f"   ❌ Error: {e}", err=True)
    
    ig_client = create_instagram_client()
    if ig_client:
        click.echo("\n📸 Fetching from Instagram...")
        try:
            metrics = ig_client.get_posts_with_metrics(since=start_date)
            all_metrics.extend(metrics)
            click.echo(f"   Found {len(metrics)} posts")
        except Exception as e:
            click.echo(f"   ❌ Error: {e}", err=True)
    
    tw_client = create_twitter_client()
    if tw_client:
        click.echo("\n🐦 Fetching from X (Twitter)...")
        try:
            metrics = tw_client.get_posts_with_metrics(since=start_date)
            all_metrics.extend(metrics)
            click.echo(f"   Found {len(metrics)} posts")
        except Exception as e:
            click.echo(f"   ❌ Error: {e}", err=True)
    
    if not all_metrics:
        enabled = config.get_enabled_platforms()
        if not enabled:
            click.echo("\n⚠️ No platforms are configured. Check your .env file.")
        else:
            click.echo(f"\n⚠️ No posts found in the last {days} days.")
        return
    
    # Update sheet
    click.echo("\n" + "=" * 60)
    click.echo("📋 Updating Google Sheet...")
    
    summary = sheets_client.batch_update_metrics(all_metrics, dry_run=dry_run)
    
    if dry_run:
        click.echo("\n🔍 DRY RUN - Changes that would be made:")
        for detail in summary["details"]:
            action = detail["action"]
            if action == "would_update":
                click.echo(f"   📝 Update: {detail['url'][:50]}...")
                click.echo(f"      Views: {detail['old_views']:,} → {detail['new_views']:,}")
                click.echo(f"      Interactions: {detail['old_interactions']:,} → {detail['new_interactions']:,}")
                click.echo(f"      Reach: {detail['old_reach']:,} → {detail['new_reach']:,}")
            elif action == "would_add":
                click.echo(f"   ➕ Add: {detail['url'][:50]}...")
                click.echo(f"      Platform: {detail['platform']}")
                click.echo(f"      Views: {detail['views']:,}, Interactions: {detail['interactions']:,}, Reach: {detail['reach']:,}")
    else:
        click.echo(f"\n   ✅ Added: {summary['added']} new posts")
        click.echo(f"   📝 Updated: {summary['updated']} existing posts")
    
    click.echo(f"\n✅ Done! {'(Dry run - no changes made)' if dry_run else ''}")


@cli.command()
def status():
    """Show configuration status and enabled platforms."""
    click.echo("\n📊 Social Media Report Generator - Status")
    click.echo("=" * 60)
    
    click.echo("\n🔌 Platform Configuration:")
    
    # Facebook
    if config.meta.facebook_enabled:
        click.echo(f"   📘 Facebook: ✅ Configured (Page ID: {config.meta.facebook_page_id})")
    else:
        click.echo("   📘 Facebook: ❌ Not configured")
        if config.meta.access_token and not config.meta.facebook_page_id:
            click.echo("      ⚠️ Missing: FACEBOOK_PAGE_ID")
        elif not config.meta.access_token:
            click.echo("      ⚠️ Missing: META_ACCESS_TOKEN")
    
    # Instagram
    if config.meta.instagram_enabled:
        click.echo(f"   📸 Instagram: ✅ Configured (Account ID: {config.meta.instagram_account_id})")
    else:
        click.echo("   📸 Instagram: ❌ Not configured")
        if config.meta.access_token and not config.meta.instagram_account_id:
            click.echo("      ⚠️ Missing: INSTAGRAM_ACCOUNT_ID")
        elif not config.meta.access_token:
            click.echo("      ⚠️ Missing: META_ACCESS_TOKEN")
    
    # Twitter
    if config.twitter.is_configured:
        click.echo(f"   🐦 Twitter/X: ✅ Configured")
    else:
        click.echo("   🐦 Twitter/X: ❌ Not configured")
        missing = []
        if not config.twitter.api_key:
            missing.append("TWITTER_API_KEY")
        if not config.twitter.bearer_token:
            missing.append("TWITTER_BEARER_TOKEN")
        if missing:
            click.echo(f"      ⚠️ Missing: {', '.join(missing)}")
    
    # Google Sheets
    click.echo("\n📋 Google Sheets:")
    if config.google_sheets.is_configured:
        click.echo(f"   ✅ Configured")
        click.echo(f"      Sheet ID: {config.google_sheets.sheet_id}")
        click.echo(f"      Credentials: {config.google_sheets.credentials_path}")
    else:
        click.echo("   ❌ Not configured")
        if not config.google_sheets.sheet_id:
            click.echo("      ⚠️ Missing: GOOGLE_SHEET_ID")
        if not config.google_sheets.credentials_path:
            click.echo("      ⚠️ Missing: GOOGLE_CREDENTIALS_PATH")
    
    # Summary
    enabled = config.get_enabled_platforms()
    click.echo("\n" + "=" * 60)
    if enabled:
        click.echo(f"✅ Ready! Enabled platforms: {', '.join(enabled)}")
    else:
        click.echo("⚠️ No platforms are configured yet.")
        click.echo("   Copy env_template.txt to .env and add your API credentials.")


@cli.command()
@click.option("--platform", "-p", type=click.Choice(["facebook", "instagram", "twitter"]), 
              prompt="Select platform", help="Social media platform")
@click.option("--post-id", "-i", default="", help="Numeric post ID (leave empty to list recent posts)")
def test(platform: str, post_id: str):
    """Test fetching metrics for a single post.
    
    \b
    For Facebook, you can either:
    - Leave post-id empty to see a list of recent posts and select one
    - Provide a NUMERIC post ID (e.g., 1234567890)
    
    \b
    NOTE: Facebook's 'pfbid' format CANNOT be used with the API.
    The Graph API only accepts numeric post IDs.
    """
    platform_emoji = {"facebook": "📘", "instagram": "📸", "twitter": "🐦"}.get(platform, "📱")
    
    metrics = None
    
    if platform == "facebook":
        client = create_facebook_client()
        if not client:
            click.echo("❌ Facebook is not configured. Check your .env file.", err=True)
            sys.exit(1)
        
        from config import config
        from dateutil import parser as date_parser
        
        # Check if pfbid format (cannot be used with API)
        if post_id and ("pfbid" in post_id):
            click.echo("\n⚠️  The 'pfbid' format CANNOT be used with Facebook's Graph API.")
            click.echo("   This is an obfuscated ID that only works in browser URLs.\n")
            click.echo("   Fetching recent posts so you can select one...\n")
            post_id = ""  # Clear to trigger list mode
        
        # If no post_id, list recent posts and let user select
        if not post_id:
            click.echo(f"{platform_emoji} Fetching recent Facebook posts...")
            click.echo("=" * 60)
            
            try:
                posts = client.get_posts_with_metrics(days=14)
                
                if not posts:
                    click.echo("❌ No posts found in the last 14 days.")
                    sys.exit(1)
                
                # Display posts with numbers
                click.echo(f"\n📋 Found {len(posts)} recent posts:\n")
                for i, p in enumerate(posts, 1):
                    caption_preview = p.caption[:45].replace("\n", " ") if p.caption else "(no caption)"
                    if len(p.caption) > 45:
                        caption_preview += "..."
                    click.echo(f"  [{i}] {p.created_time.strftime('%Y-%m-%d %H:%M')} | {caption_preview}")
                    click.echo(f"      Views: {p.views:,} | Interactions: {p.interactions:,} | Reach: {p.reach:,}")
                    click.echo("")
                
                # Ask user to select
                choice = click.prompt("\nEnter post number to see full details", type=int)
                
                if choice < 1 or choice > len(posts):
                    click.echo("❌ Invalid selection.")
                    sys.exit(1)
                
                metrics = posts[choice - 1]
                
            except Exception as e:
                click.echo(f"❌ Error fetching posts: {e}", err=True)
                sys.exit(1)
        else:
            # Direct lookup by numeric ID
            click.echo(f"\n{platform_emoji} Fetching Facebook post: {post_id}")
            click.echo("=" * 60)
            
            try:
                # Build full post ID: {page_id}_{post_id}
                if "_" in post_id:
                    full_post_id = post_id
                else:
                    full_post_id = f"{config.meta.facebook_page_id}_{post_id}"
                
                click.echo(f"   Looking up: {full_post_id}")
                
                # Get post data
                post_data = client._make_request(
                    full_post_id,
                    params={"fields": "id,message,created_time,permalink_url"}
                )
                
                created_time = date_parser.parse(post_data["created_time"])
                caption = post_data.get("message", "")
                
                # Get insights
                insights = client.get_post_insights(full_post_id)
                
                metrics = PostMetrics(
                    post_id=full_post_id,
                    post_url=post_data.get("permalink_url", ""),
                    platform="facebook",
                    created_time=created_time,
                    caption=caption,
                    views=insights["views"],
                    interactions=insights["interactions"],
                    reach=insights["reach"],
                    follows=insights["follows"],
                    link_clicks=insights["link_clicks"],
                    likes=insights["likes"],
                    comments=insights["comments"],
                    shares=insights["shares"],
                )
            except Exception as e:
                click.echo(f"❌ Error: {e}", err=True)
                click.echo("\n💡 The post ID must be NUMERIC (e.g., 1234567890)")
                click.echo("   Run without -i to see a list of recent posts:")
                click.echo("   python3 main.py test -p facebook")
                sys.exit(1)
    
    elif platform == "instagram":
        client = create_instagram_client()
        if not client:
            click.echo("❌ Instagram is not configured. Check your .env file.", err=True)
            sys.exit(1)
        
        # For Instagram, build URL from shortcode and fetch
        url = f"https://www.instagram.com/p/{post_id}/"
        metrics = client.get_metrics_for_url(url)
    
    elif platform == "twitter":
        client = create_twitter_client()
        if not client:
            click.echo("❌ Twitter is not configured. Check your .env file.", err=True)
            sys.exit(1)
        
        url = f"https://twitter.com/i/status/{post_id}"
        metrics = client.get_metrics_for_url(url)
    
    # Display results
    if metrics:
        click.echo("\n📊 POST METRICS")
        click.echo("-" * 40)
        click.echo(f"   📅 Date: {metrics.created_time.strftime('%Y-%m-%d %H:%M')}")
        click.echo(f"   🔗 URL: {metrics.post_url}")
        
        if metrics.caption:
            click.echo(f"\n   📝 Caption:")
            # Show full caption with word wrap
            caption_lines = metrics.caption.split("\n")
            for line in caption_lines[:5]:  # Show first 5 lines
                click.echo(f"      {line[:80]}")
            if len(caption_lines) > 5:
                click.echo(f"      ... ({len(caption_lines) - 5} more lines)")
        
        click.echo(f"\n   {'─' * 35}")
        click.echo(f"   👁️  Views:        {metrics.views:>10,}")
        click.echo(f"   💬  Interactions: {metrics.interactions:>10,}")
        click.echo(f"   👥  Reach:        {metrics.reach:>10,}")
        click.echo(f"   ➕  Follows:      {metrics.follows:>10,}")
        click.echo(f"   🔗  Link Clicks:  {metrics.link_clicks:>10,}")
        click.echo(f"   {'─' * 35}")
        click.echo(f"   ❤️  Likes:        {metrics.likes:>10,}")
        click.echo(f"   💬  Comments:     {metrics.comments:>10,}")
        click.echo(f"   🔄  Shares:       {metrics.shares:>10,}")
        click.echo(f"   {'─' * 35}")
        
        click.echo("\n✅ Done!")
    else:
        click.echo(f"\n❌ Could not fetch metrics for post: {post_id}")
        click.echo("   Check that:")
        click.echo("   - The post ID is correct")
        click.echo("   - You have access to this post's insights")
        click.echo("   - Your API token has the required permissions")


if __name__ == "__main__":
    cli()

