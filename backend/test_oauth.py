#!/usr/bin/env python3
"""Test OAuth module and FastAPI app startup"""

import sys
import asyncio

async def test_imports():
    """Test that all modules import correctly"""
    try:
        print("Testing imports...")
        from app.core.config import settings
        print(f"✅ Settings loaded: WECHAT_APP_ID={settings.WECHAT_APP_ID[:10] if settings.WECHAT_APP_ID else 'NOT SET'}...")
        
        from app.api.wechat_login import router, oauth_client
        print(f"✅ OAuth router imported successfully")
        
        from app.main import app
        print(f"✅ FastAPI app imported successfully")
        
        # Check if router is registered
        if not any(r.path == "/api/wechat-auth/qrcode/generate" for r in app.routes):
            print("⚠️  Warning: OAuth routes not found in app.routes")
        else:
            print("✅ OAuth routes registered with app")
        
        print("\n✅ All imports successful!")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_imports()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
