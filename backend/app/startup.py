"""Resilient startup handler with comprehensive logging."""

import sys
import os
from pathlib import Path
import time


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
    global_start = time.time()
    
    print("🚀 Initializing application components...\n")
    
    try:
        print(f"[{time.time()-global_start:.2f}s] Importing modules...")
        from . import state
        from .ingestion.loader import ingest_mock_feed, ingest_kaggle_dataset
        from .clustering.engine import build_story_clusters
        print(f"[{time.time()-global_start:.2f}s] ✅ Modules imported\n")
    except Exception as e:
        print(f"[{time.time()-global_start:.2f}s] ❌ FATAL: Failed to import modules: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Check if already initialized
    if state.startup_complete:
        print(f"[{time.time()-global_start:.2f}s] ✅ Startup already completed in previous run, resuming...\n")
        return
    
    # Phase 1: WebHose
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 1/4] Loading WebHose articles...")
    phase1_start = time.time()
    try:
        count = ingest_mock_feed()
        phase1_time = time.time() - phase1_start
        print(f"[{time.time()-global_start:.2f}s] ✅ WebHose: {count} articles loaded ({phase1_time:.2f}s)\n")
    except Exception as e:
        phase1_time = time.time() - phase1_start
        print(f"[{time.time()-global_start:.2f}s] ❌ WebHose failed after {phase1_time:.2f}s (continuing): {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Phase 2: Kaggle
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 2/4] Loading Kaggle dataset...")
    phase2_start = time.time()
    try:
        count = ingest_kaggle_dataset()
        phase2_time = time.time() - phase2_start
        print(f"[{time.time()-global_start:.2f}s] ✅ Kaggle: {count} articles loaded ({phase2_time:.2f}s)")
        print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}\n")
    except Exception as e:
        phase2_time = time.time() - phase2_start
        print(f"[{time.time()-global_start:.2f}s] ❌ Kaggle failed after {phase2_time:.2f}s (continuing): {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Mark startup complete
    print(f"[{time.time()-global_start:.2f}s] ✅ [Phase 3/4] Startup checkpoint saved")
    state.startup_complete = True
    print(f"[{time.time()-global_start:.2f}s] 💾 state.startup_complete = True\n")
    
    # Phase 4: Background clustering (non-blocking)
    print(f"[{time.time()-global_start:.2f}s] 🔄 [Phase 4/4] Starting background clustering...")
    try:
        import threading
        
        def cluster_worker():
            cluster_start = time.time()
            try:
                print(f"[{time.time()-global_start:.2f}s]    🔄 Clustering {len(state.articles)} articles...")
                count = build_story_clusters()
                cluster_time = time.time() - cluster_start
                print(f"[{time.time()-global_start:.2f}s]    ✅ Clustering complete: {count} clusters ({cluster_time:.2f}s)\n")
            except Exception as cluster_err:
                cluster_time = time.time() - cluster_start
                print(f"[{time.time()-global_start:.2f}s]    ⚠️  Clustering failed after {cluster_time:.2f}s (non-critical): {type(cluster_err).__name__}: {cluster_err}\n")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=cluster_worker, daemon=True, name="ClusterWorker")
        thread.start()
        print(f"[{time.time()-global_start:.2f}s] ✅ Background clustering thread started\n")
    except Exception as e:
        print(f"[{time.time()-global_start:.2f}s] ⚠️  Threading setup failed: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    total_time = time.time() - global_start
    print("="*60)
    print("✅ APPLICATION STARTUP COMPLETE")
    print("="*60)
    print(f"Total startup time: {total_time:.2f}s")
    print(f"Articles: {len(state.articles)}")
    print(f"Categories: {len(state.available_categories)}")
    print(f"Clusters: {len(state.clusters)}")
    print(f"Server should be accepting requests now")
    print("="*60 + "\n")
