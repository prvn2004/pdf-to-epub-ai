"""
Folio — PDF → Markdown Live
============================
Entrypoint script for starting the Folio FastAPI application.
"""

import os
import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    if not settings.OPENCODE_API_KEY:
        print("⚠️  OPENCODE_API_KEY not set in .env file!")
        print("   Get your key at: https://opencode.ai/auth")
        print("   Then add: OPENCODE_API_KEY=your-key-here to .env")
        print()
    uvicorn.run(app, host="0.0.0.0", port=8765)
