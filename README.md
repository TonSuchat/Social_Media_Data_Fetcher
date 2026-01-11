# 📊 Social Media Weekly Report Generator

Automatically fetch engagement and reach metrics from Facebook, Instagram, and X (Twitter), then update your Google Sheet!

## ✨ Features

- 📱 **Multi-platform support**: Facebook Pages, Instagram Business, X (Twitter)
- 📈 **Metrics collected**: Engagement (likes, comments, shares), Reach/Impressions
- 📋 **Google Sheets integration**: Auto-updates your tracking spreadsheet
- ⏰ **Scheduling**: Run weekly or on-demand
- 🔗 **Post URL detection**: Automatically identifies platform from post URLs

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd weekly_report_generator
pip install -r requirements.txt
```

### 2. Set Up API Credentials

Copy the template environment file and fill in your credentials:

```bash
cp env_template.txt .env
```

Edit `.env` with your API keys (see setup guides below).

### 3. Run the Script

```bash
# Fetch metrics for all posts from the last 7 days
python main.py fetch --days 7

# Update Google Sheet with latest metrics
python main.py update-sheet

# Run both (fetch + update)
python main.py run
```

---

## 🔐 API Setup Guides

### Facebook & Instagram (Meta Graph API)

Facebook and Instagram both use Meta's Graph API.

1. **Create a Meta Developer App**:

   - Go to [Meta for Developers](https://developers.facebook.com/)
   - Create a new app → Select "Business" type
   - Add the "Facebook Login" and "Instagram Graph API" products

2. **Get Access Tokens**:

   - For Facebook Pages: You need a Page Access Token with `pages_read_engagement`, `pages_show_list` permissions
   - For Instagram Business: Link your Instagram Business account to a Facebook Page, then use the Page Access Token

3. **Generate Long-Lived Access Token** (recommended):

   Short-lived tokens expire in ~1-2 hours. Follow these steps to get a long-lived token:

   **Step 1: Get a Short-Lived User Token**

   - Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
   - Select your app from the dropdown
   - Click "Generate Access Token" and grant the required permissions
   - Copy the generated token

   **Step 2: Exchange for Long-Lived Token (~60 days)**

   Make a GET request to:

   ```
   https://graph.facebook.com/v18.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id={YOUR_APP_ID}&
     client_secret={YOUR_APP_SECRET}&
     fb_exchange_token={SHORT_LIVED_TOKEN}
   ```

   Or use curl:

   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
   ```

   **Step 3: Get Never-Expiring Page Access Token**

   Exchange your long-lived user token for a page token (which never expires):

   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/me/accounts?access_token={LONG_LIVED_USER_TOKEN}"
   ```

   This returns page access tokens for all pages you manage. Use the `access_token` field from the response.

   | Token Type                              | Lifespan          |
   | --------------------------------------- | ----------------- |
   | Short-lived User Token                  | ~1-2 hours        |
   | Long-lived User Token                   | ~60 days          |
   | Page Token (from long-lived user token) | **Never expires** |

4. **Get Page/Account IDs**:

   - Facebook Page ID: Found in Page Settings → About
   - Instagram Business Account ID: Use Graph API Explorer to query `/me/accounts` then `/{page-id}?fields=instagram_business_account`

5. **Add to `.env`**:
   ```
   META_ACCESS_TOKEN=your_page_access_token
   FACEBOOK_PAGE_ID=your_facebook_page_id
   INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id
   ```

> 💡 **Tip**: Use [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/) to test and generate tokens.

#### ⚠️ Important: Facebook App Review

**Without App Review**, you can only fetch:

- ✅ Post content, dates, URLs
- ✅ Shares count

**With App Review approval**, you can also fetch:

- ❤️ Reactions/Likes count
- 💬 Comments count
- 👁️ Views/Impressions (requires `read_insights`)
- 👥 Reach (requires `read_insights`)

To submit for App Review:

1. Go to your app's [App Review](https://developers.facebook.com/apps/YOUR_APP_ID/app-review/permissions-and-features/)
2. Request `pages_read_engagement` permission
3. Explain your use case (e.g., "Business reporting for Page engagement")
4. Wait for approval (1-5 business days)

### X (Twitter) API

1. **Apply for Developer Access**:

   - Go to [Twitter Developer Portal](https://developer.twitter.com/)
   - Create a project and app
   - You need at least "Basic" access tier for engagement metrics

2. **Generate API Keys**:

   - In your app settings, generate:
     - API Key and Secret
     - Access Token and Secret (for your account)
     - Bearer Token

3. **Add to `.env`**:
   ```
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_SECRET=your_access_secret
   TWITTER_BEARER_TOKEN=your_bearer_token
   ```

### Google Sheets API

1. **Create Google Cloud Project**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable "Google Sheets API" and "Google Drive API"

2. **Create Service Account**:

   - Go to "APIs & Services" → "Credentials"
   - Create a Service Account
   - Download the JSON key file
   - Save it as `credentials/google_service_account.json`

3. **Share Your Spreadsheet**:

   - Open your Google Sheet
   - Share it with the service account email (found in the JSON file)
   - Give "Editor" access

4. **Add to `.env`**:
   ```
   GOOGLE_SHEET_ID=1osJcPPuZFXIQhXk3NXvuMeWi3mJ9e72YoHm_MF_tB6A
   GOOGLE_CREDENTIALS_PATH=credentials/google_service_account.json
   ```

> The spreadsheet ID is in the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`

---

## 📋 Google Sheet Format

Your Google Sheet will have these columns (auto-created):

| Date       | Time  | Platform | Post URL    | Caption    | Views  | Interactions | Reach  | Follows | Link Clicks | Likes | Comments | Shares |
| ---------- | ----- | -------- | ----------- | ---------- | ------ | ------------ | ------ | ------- | ----------- | ----- | -------- | ------ |
| 2024-01-15 | 14:30 | Facebook | https://... | My post... | 15,068 | 92           | 10,029 | 0       | 5           | 81    | 1        | 19     |

**Column Definitions:**

- **Views** - Total impressions (how many times the post was shown)
- **Interactions** - Total engagement (reactions + comments + shares + link clicks)
- **Reach** - Unique viewers (how many different people saw the post)
- **Follows** - New followers gained from this post
- **Link Clicks** - Number of clicks on links in the post

The script will:

- Find existing rows by matching the Post URL
- Update all metrics columns with fresh data
- Add new posts if they don't exist

---

## 🛠️ Advanced Usage

### Fetch from Specific Platform

```bash
python main.py fetch --platform facebook
python main.py fetch --platform instagram
python main.py fetch --platform twitter
```

### Custom Date Range

```bash
python main.py fetch --days 14  # Last 14 days
python main.py fetch --since 2024-01-01  # Since specific date
```

### Schedule Weekly Runs

```bash
# Run every Sunday at 9 AM
python main.py schedule --day sunday --time 09:00
```

### Dry Run (Preview without updating)

```bash
python main.py run --dry-run
```

---

## 📁 Project Structure

```
weekly_report_generator/
├── main.py                 # CLI entry point
├── config.py               # Configuration loader
├── platforms/
│   ├── __init__.py
│   ├── facebook_api.py     # Facebook Graph API client
│   ├── instagram_api.py    # Instagram Graph API client
│   └── twitter_api.py      # X/Twitter API client
├── sheets/
│   ├── __init__.py
│   └── google_sheets.py    # Google Sheets integration
├── utils/
│   ├── __init__.py
│   └── url_parser.py       # Parse post URLs to identify platform
├── credentials/            # Store API credentials here (gitignored)
├── .env                    # Environment variables (gitignored)
├── .env.example            # Template for .env
└── requirements.txt
```

---

## 🐛 Troubleshooting

### "Token expired" errors

- Meta tokens expire! Use a long-lived token or refresh it periodically
- Run: `python main.py refresh-token --platform meta`

### "Rate limited" errors

- The script has built-in rate limiting, but if you hit limits:
- Wait 15 minutes and try again
- Reduce the date range

### "Permission denied" on Google Sheets

- Make sure you shared the sheet with the service account email
- Check the service account has "Editor" access

---

## 📝 License

MIT - Feel free to modify for your needs!
