"""Run the SOC advisor FastAPI app with a beginner-friendly command."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
load_dotenv(PROJECT_ROOT / ".env")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("soc_advisor.main:app", host="127.0.0.1", port=port, reload=True)
