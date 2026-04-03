#!/usr/bin/env python3
"""
Download Webhose Free News Datasets

This script downloads the latest news datasets from: https://github.com/Webhose/free-news-datasets
Usage: python3 download_webhose_datasets.py [topic]
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# Map of available datasets
DATASETS = {
    "finance": "Finance news and market data",
    "politics": "Political news and elections",
    "tech": "Technology and AI news",
    "sports": "Sports news",
    "climate": "Climate and environment news",
    "health": "Medical and health news",
}


def download_dataset(topic: str, output_dir: str) -> bool:
    """Download a specific dataset by topic."""
    
    # GitHub raw content URLs
    base_url = "https://raw.githubusercontent.com/Webhose/free-news-datasets/master/News_Datasets"
    
    # Common dataset file patterns
    file_patterns = [
        f"{topic}_sample.json",
        f"{topic}_20231013.json",
        f"{topic}_latest.json",
        f"{topic}.json",
    ]
    
    output_path = Path(output_dir) / f"{topic}_webhose.json"
    
    for pattern in file_patterns:
        url = f"{base_url}/{pattern}"
        print(f"Trying: {pattern}...", end=" ")
        
        try:
            urllib.request.urlretrieve(url, str(output_path))
            
            # Verify file is valid JSON
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            # Count articles/posts
            if isinstance(data, dict):
                count = len(data.get("posts", []))
            else:
                count = len(data) if isinstance(data, list) else 0
            
            print(f"✓ Downloaded ({count} articles)")
            return True
            
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Not found")
                continue
            else:
                print(f"Error: {e}")
                return False
        except json.JSONDecodeError:
            print(f"Invalid JSON - skipping")
            continue
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    print(f"✗ Could not find {topic} dataset")
    return False


def list_datasets():
    """List available datasets."""
    print("\n📰 Available Webhose Datasets:")
    print("-" * 50)
    for topic, desc in DATASETS.items():
        print(f"  {topic:12} - {desc}")
    print("-" * 50)


def main():
    import sys
    
    output_dir = Path(__file__).parent.parent / "webhose_extended"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if len(sys.argv) > 1:
        topics = sys.argv[1:]
    else:
        # Download all topics
        topics = list(DATASETS.keys())
        list_datasets()
    
    print(f"\n📥 Downloading datasets to: {output_dir}\n")
    
    successful = 0
    for topic in topics:
        if topic.lower() in DATASETS:
            if download_dataset(topic.lower(), str(output_dir)):
                successful += 1
        else:
            print(f"Unknown topic: {topic}")
            list_datasets()
    
    print(f"\n✓ Successfully downloaded {successful}/{len(topics)} datasets")
    print(f"\nTo use these datasets in Synergy:")
    print(f"  from app.ingestion.webhose_loader import load_webhose_sample_datasets")
    print(f"  articles = load_webhose_sample_datasets()")
    

if __name__ == "__main__":
    main()
