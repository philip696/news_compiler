# Webhose Free News Datasets Integration Guide

## Quick Start

You've successfully set up the Webhose dataset integration for your Synergy news platform. Here's how to use it:

### Step 1: Download Datasets

Visit: **https://github.com/Webhose/free-news-datasets**

1. Click on the **News_Datasets** folder
2. Browse available JSON files (finance, tech, politics, sports, climate, health, etc.)
3. Click on a JSON file → **Download** button
4. Save to: `backend/data/webhose_extended/`

**Example**: Download `finance_20250101.json` to get 1000+ finance articles

### Step 2: Verify Downloads

```bash
ls backend/data/webhose_extended/*.json
```

You should see your downloaded .json files in that directory.

### Step 3: Load Datasets into Synergy

The application automatically loads all JSON files from `webhose_extended/` directory.

**Option A: Automatic (recommended)**
- Datasets load automatically on app startup
- No code changes needed

**Option B: Manual Load**
```python
from app.ingestion.webhose_loader import load_webhose_sample_datasets, enrich_state_with_webhose

# Load all datasets from webhose_extended/
articles = load_webhose_sample_datasets()

# Add to application
enrich_state_with_webhose(articles)
```

### Step 4: Restart Backend

```bash
# Kill existing process
lsof -i :8007 | grep -v COMMAND | awk '{print $2}' | xargs kill -9

# Start fresh
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

Articles from Webhose datasets will now appear in your Synergy feed alongside existing data!

---

## Available Topics

Webhose releases datasets on various topics with ~1000 articles each:

| Topic | Description | Use Case |
|-------|-------------|----------|
| **Finance** | Market news, earnings, crypto, stocks | Investment tracking |
| **Technology** | AI, startups, gadgets, software | Tech industry insights |
| **Politics** | Elections, policy, government | Political awareness |
| **Sports** | Games, players, leagues, events | Sports coverage |
| **Climate** | Environment, sustainability, weather | Climate tracking |
| **Health** | Medical research, diseases, wellness | Health news |
| **Science** | Physics, biology, astronomy | Scientific discoveries |
| **Business** | Corporate news, M&A, economy | Business intelligence |

---

## File Format

Webhose datasets are JSON with this structure:

```json
{
  "posts": [
    {
      "title": "Tesla Launches New Model",
      "text": "Full article content here...",
      "url": "https://news.example.com/article",
      "published": "2025-01-15T10:30:00Z",
      "thread": {
        "site": "example.com",
        "published": "2025-01-15T10:30:00Z"
      },
      "author": "John Doe",
      "entities": [...],
      "tags": [...]
    }
  ]
}
```

---

## Integration Details

### Files Created

```
backend/
├── app/ingestion/
│   └── webhose_loader.py         # Dataset loader
├── scripts/
│   └── download_webhose_datasets.py  # Download script
└── data/
    └── webhose_extended/
        ├── README.md              # This guide
        └── *.json                 # Your downloaded datasets
```

### How It Works

1. **webhose_loader.py** - Parses Webhose JSON format and converts to Synergy internal format
2. **Auto-load** - Application loads all JSON files from `webhose_extended/` on startup
3. **Clustering** - Articles get clustered with existing data automatically
4. **Embeddings** - Text embeddings generated on-the-fly for similarity matching

---

## Tips & Tricks

### Batch Download

If you want multiple datasets, download them one by one from GitHub:
- Finance: `finance_*.json`
- Tech: `tech_*.json`
- Politics: `politics_*.json`
- etc.

### Memory Usage

Each dataset adds ~10-30MB to memory. Start with 1-2 datasets:
- First dataset: Good for testing
- 3-5 datasets: Comprehensive coverage
- 10+ datasets: Full platform experience

### Update Datasets Weekly

Webhose releases new datasets every week. Download fresh ones monthly:
1. Go to GitHub repository
2. Download latest files with new dates
3. Replace old files in `webhose_extended/`
4. Restart backend

### Custom Integration

Need to process datasets differently? Edit `webhose_loader.py`:

```python
def load_webhose_json(json_data):
    # Customize parsing here
    # Add custom field mappings
    # Filter articles by criteria
    pass
```

---

## Troubleshooting

**Q: Datasets not loading?**
A: 
- Check files are in `backend/data/webhose_extended/`
- Verify JSON is valid: `python -m json.tool filename.json`
- Check backend logs on restart

**Q: Too many articles?**
A:
- Start with 1 dataset
- Add more as needed
- Or edit `webhose_loader.py` to filter by date

**Q: Want different topics?**
A:
- Download different datasets from Webhose
- Replace files in `webhose_extended/`
- Restart backend

---

## Terms of Use

By using Webhose datasets, you agree to their terms:
- Free for **academic, research, and journalistic purposes**
- Proper attribution required
- See: https://github.com/Webhose/free-news-datasets/blob/master/tou.MD

---

## Next Steps

1. **Download your first dataset** (e.g., finance)
2. **Place in** `backend/data/webhose_extended/`
3. **Restart backend** to load
4. **Check Synergy feed** for new articles
5. **Download more datasets** based on your interests

Enjoy your expanded news coverage with Synergy!
