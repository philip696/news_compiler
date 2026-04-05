"""Resilient startup handler with comprehensive logging."""

import sys
import os
from pathlib import Path


def setup_startup_logging():
    """Configure logging for startup diagnostics."""
    log_file = Path("/tmp/geb_startup.log")
    
    class DualWriter:
        """Write to both stdout and a log file."""
        def __init__(self, stdout, logfile):
            self.stdout = stdout
            self.logfile = logfile
        
        def write(self, msg):
            self.stdout.write(msg)
            try:
                with open(self.logfile, "a") as f:
                    f.write(msg)
            except:
                pass
        
        def flush(self):
            self.stdout.flush()
    
    sys.stdout = DualWriter(sys.stdout, log_file)
    sys.stderr = DualWriter(sys.stderr, log_file)
    
    print(f"\n{'='*60}")
    print(f"GEB Application Starting at {log_file}")
    print(f"Python: {sys.version}")
    print(f"Path: {os.getcwd()}")
    print(f"{'='*60}\n")


def run_startup_sequence():
    """Run the startup sequence with maximum resilience."""
    print("🚀 Initializing application components...\n")
    
    try:
        from . import state
        from .ingestion.loader import ingest_mock_feed, ingest_kaggle_dataset
        from .clustering.engine import build_story_clusters
    except Exception as e:
        print(f"❌ FATAL: Failed to import modules: {e}")
        raise
    
    # Check if already initialized
    if state.startup_complete:
        print("✅ Startup already completed in previous run, resuming...\n")
        return
    
    # Phase 1: WebHose
    print("📥 [Phase 1/4] Loading WebHose articles...")
    try:
        count = ingest_mock_feed()
        print(f"   ✅ WebHose: {count} articles loaded\n")
    except Exception as e:
        print(f"   ⚠️  WebHose failed (continuing): {type(e).__name__}: {e}\n")
    
    # Phase 2: Kaggle
    print("📥 [Phase 2/4] Loading Kaggle dataset...")
    try:
        count = ingest_kaggle_dataset()
        print(f"   ✅ Kaggle: {count} articles loaded")
        print(f"   📊 Total articles: {len(state.articles)}\n")
    except Exception as e:
        print(f"   ⚠️  Kaggle failed (continuing): {type(e).__name__}: {e}\n")
    
    # Mark startup complete
    state.startup_complete = True
    print(f"✅ [Phase 3/4] Startup checkpoint saved\n")
    
    # Phase 4: Background clustering (non-blocking)
    print("🔄 [Phase 4/4] Starting background clustering...")
    try:
        import threading
        
        def cluster_worker():
            try:
                print(f"   🔄 Clustering {len(state.articles)} articles...")
                count = build_story_clusters()
                print(f"   ✅ Clustering complete: {count} story clusters created\n")
            except Exception as cluster_err:
                print(f"   ⚠️  Clustering failed (non-critical): {type(cluster_err).__name__}: {cluster_err}\n")
        
        thread = threading.Thread(target=cluster_worker, daemon=True, name="ClusterWorker")
        thread.start()
        print("   ✅ Background clustering thread started\n")
    except Exception as e:
        print(f"   ⚠️  Threading setup failed: {type(e).__name__}: {e}\n")
    
    print("="*60)
    print("✅ APPLICATION STARTUP COMPLETE")
    print("="*60)
    print(f"Articles: {len(state.articles)}")
    print(f"Categories: {len(state.available_categories)}")
    print(f"Clusters: {len(state.clusters)}")
    print("="*60 + "\n")
