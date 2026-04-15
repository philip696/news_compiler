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


async def run_startup_sequence():
    """Run the startup sequence with maximum resilience."""
    global_start = time.time()
    
    print("🚀 Initializing application components...\n")
    
    try:
        print(f"[{time.time()-global_start:.2f}s] Importing modules...")
        from . import state
        from .ingestion.loader import ingest_webhose_jsonl, ingest_kaggle_dataset, ingest_yahoo_finance_articles, ingest_defeatbeta_articles
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
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 1/6] Loading WebHose articles...")
    phase1_start = time.time()
    try:
        count = ingest_webhose_jsonl()
        phase1_time = time.time() - phase1_start
        print(f"[{time.time()-global_start:.2f}s] ✅ WebHose: {count} articles loaded ({phase1_time:.2f}s)\n")
    except Exception as e:
        phase1_time = time.time() - phase1_start
        print(f"[{time.time()-global_start:.2f}s] ❌ WebHose failed after {phase1_time:.2f}s (continuing): {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Phase 2: DefeatBeta API (PRIMARY) - High-quality financial analysis
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 2/6] Loading DefeatBeta API articles (PRIMARY)...")
    phase2_start = time.time()
    defeatbeta_count = 0
    
    try:
        defeatbeta_count = await ingest_defeatbeta_articles()
    except Exception as e:
        phase2_time = time.time() - phase2_start
        print(f"[{time.time()-global_start:.2f}s] ⚠️  DefeatBeta API failed after {phase2_time:.2f}s: {type(e).__name__}\n")
    
    phase2_time = time.time() - phase2_start
    if defeatbeta_count > 0:
        print(f"[{time.time()-global_start:.2f}s] ✅ DefeatBeta (PRIMARY): {defeatbeta_count} articles loaded ({phase2_time:.2f}s)\n")
    else:
        print(f"[{time.time()-global_start:.2f}s] ⚠️  DefeatBeta (PRIMARY) delivered 0 articles ({phase2_time:.2f}s)")
        print(f"[{time.time()-global_start:.2f}s] 📥 Falling back to Yahoo Finance and Kaggle...\n")
    
    # Phase 3: Yahoo Finance API (SECONDARY) - if DefeatBeta delivered < 100 articles
    if defeatbeta_count < 100:
        print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 3/6] Loading Yahoo Finance articles (SECONDARY)...")
        phase3_start = time.time()
        yahoo_count = 0
        
        try:
            yahoo_count = await ingest_yahoo_finance_articles()
        except Exception as e:
            phase3_time = time.time() - phase3_start
            print(f"[{time.time()-global_start:.2f}s] ⚠️  Yahoo Finance API failed after {phase3_time:.2f}s: {type(e).__name__}\n")
        
        phase3_time = time.time() - phase3_start
        if yahoo_count > 0:
            print(f"[{time.time()-global_start:.2f}s] ✅ Yahoo Finance (SECONDARY): {yahoo_count} articles loaded ({phase3_time:.2f}s)")
            print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}\n")
        else:
            print(f"[{time.time()-global_start:.2f}s] ⚠️  Yahoo Finance (SECONDARY) delivered 0 articles ({phase3_time:.2f}s)")
            print(f"[{time.time()-global_start:.2f}s] 📥 Falling back to Kaggle dataset...\n")
            yahoo_count = 0
    else:
        print(f"[{time.time()-global_start:.2f}s] ✅ DefeatBeta (PRIMARY) delivered sufficient data ({defeatbeta_count} articles)")
        print(f"[{time.time()-global_start:.2f}s] ⏭️  Skipping Yahoo Finance SECONDARY phase")
        print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}\n")
        yahoo_count = 0
    
    # Phase 4: Kaggle (FALLBACK - only if DefeatBeta + Yahoo Finance didn't deliver enough)
    total_real_sources = defeatbeta_count + yahoo_count
    if total_real_sources < 200:  # If real sources didn't provide substantial data
        print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 4/6] Loading Kaggle dataset (FALLBACK)...")
        phase4_start = time.time()
        kaggle_count = 0
        try:
            kaggle_count = ingest_kaggle_dataset()
            phase4_time = time.time() - phase4_start
            total_loaded = defeatbeta_count + yahoo_count + kaggle_count
            print(f"[{time.time()-global_start:.2f}s] ✅ Kaggle (FALLBACK): {kaggle_count} articles loaded ({phase4_time:.2f}s)")
            print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}")
            print(f"[{time.time()-global_start:.2f}s]    → DefeatBeta: {defeatbeta_count} | Yahoo Finance: {yahoo_count} | Kaggle: {kaggle_count}\n")
        except Exception as e:
            phase4_time = time.time() - phase4_start
            print(f"[{time.time()-global_start:.2f}s] ❌ Kaggle fallback failed after {phase4_time:.2f}s: {type(e).__name__}: {e}\n")
            import traceback
            traceback.print_exc()
    else:
        print(f"[{time.time()-global_start:.2f}s] ✅ Real sources (DefeatBeta + Yahoo) delivered sufficient data ({total_real_sources} articles)")
        print(f"[{time.time()-global_start:.2f}s] ⏭️  Skipping Kaggle fallback phase\n")
    
    # Phase 5: Startup checkpoint - mark startup complete
    print(f"[{time.time()-global_start:.2f}s] ✅ [Phase 5/6] Startup checkpoint saved")
    state.startup_complete = True
    print(f"[{time.time()-global_start:.2f}s] 💾 state.startup_complete = True")
    print(f"[{time.time()-global_start:.2f}s] 📊 Articles loaded: {len(state.articles)} across {len(state.available_categories)} categories\n")
    
    # Phase 6: Background clustering (non-blocking)
    print(f"[{time.time()-global_start:.2f}s] 🔄 [Phase 6/6] Starting background clustering...")
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
