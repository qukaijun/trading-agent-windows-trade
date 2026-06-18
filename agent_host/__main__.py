from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Trading Agent Assistant local server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    uvicorn.run(
        "agent_host.server:app",
        host=args.host,
        port=args.port,
        reload=False,
        app_dir=str(root),
    )


if __name__ == "__main__":
    main()

