"""Startup handler — loads data into in-memory state on server boot."""

import logging
import sys
import time

logger = logging.getLogger("uvicorn.error")


def _log(msg: str):
    """Log through uvicorn so output is visible in the terminal."""
    logger.info(msg)
    # also flush to stdout as a backup
    print(msg, flush=True)
    sys.stdout.flush()


def run_startup_sequence():
    """Run the startup sequence with maximum resilience."""
    global_start = time.time()

    _log("=" * 60)
    _log("🚀 GEB startup sequence beginning...")
    _log("=" * 60)

    try:
        _log(f"[{time.time()-global_start:.2f}s] Importing modules...")
        from . import state
        from .ingestion.loader import ingest_mock_feed, ingest_kaggle_dataset
        from .clustering.engine import build_story_clusters
        _log(f"[{time.time()-global_start:.2f}s] ✅ Modules imported")
    except Exception as e:
        _log(f"[{time.time()-global_start:.2f}s] ❌ FATAL: Failed to import modules: {e}")
        import traceback
        traceback.print_exc()
        raise

    if state.startup_complete:
        _log(f"[{time.time()-global_start:.2f}s] ✅ Already initialized, skipping.")
        return

    # Phase 1: WebHose (main feed)
    _log(f"[{time.time()-global_start:.2f}s] 📥 Phase 1 — Loading WebHose articles...")
    t0 = time.time()
    try:
        web_count = ingest_mock_feed()
        _log(f"[{time.time()-global_start:.2f}s] ✅ WebHose: {web_count} articles ({time.time()-t0:.2f}s)")
    except Exception as e:
        _log(f"[{time.time()-global_start:.2f}s] ❌ WebHose failed ({time.time()-t0:.2f}s): {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

    # Phase 2: Kaggle (explore feed)
    _log(f"[{time.time()-global_start:.2f}s] 📥 Phase 2 — Loading Kaggle dataset...")
    t0 = time.time()
    try:
        kaggle_count = ingest_kaggle_dataset()
        _log(f"[{time.time()-global_start:.2f}s] ✅ Kaggle: {kaggle_count} articles ({time.time()-t0:.2f}s)")
        _log(f"[{time.time()-global_start:.2f}s] 📊 Total in state.articles: {len(state.articles)}")
        _log(f"[{time.time()-global_start:.2f}s] 📊 state.articles_explore: {len(state.articles_explore)}")
        _log(f"[{time.time()-global_start:.2f}s] 📊 Categories: {state.available_categories}")
    except Exception as e:
        _log(f"[{time.time()-global_start:.2f}s] ❌ Kaggle failed ({time.time()-t0:.2f}s): {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

    state.startup_complete = True
    _log(f"[{time.time()-global_start:.2f}s] ✅ state.startup_complete = True")

    # Phase 3: Background clustering
    _log(f"[{time.time()-global_start:.2f}s] 🔄 Phase 3 — Starting background clustering thread...")
    try:
        import threading

        def cluster_worker():
            t_start = time.time()
            try:
                _log(f"  🔄 Clustering {len(state.articles)} articles...")
                count = build_story_clusters()
                _log(f"  ✅ Clustering done: {count} clusters ({time.time()-t_start:.2f}s)")
            except Exception as err:
                _log(f"  ⚠️  Clustering failed ({time.time()-t_start:.2f}s): {type(err).__name__}: {err}")
                import traceback; traceback.print_exc()

        thread = threading.Thread(target=cluster_worker, daemon=True, name="ClusterWorker")
        thread.start()
        _log(f"[{time.time()-global_start:.2f}s] ✅ Clustering thread started")
    except Exception as e:
        _log(f"[{time.time()-global_start:.2f}s] ⚠️  Threading setup failed: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

    _log("=" * 60)
    _log(f"✅ STARTUP COMPLETE in {time.time()-global_start:.2f}s")
    _log(f"   articles={len(state.articles)}  explore={len(state.articles_explore)}  clusters={len(state.clusters)}")
    _log("=" * 60)
