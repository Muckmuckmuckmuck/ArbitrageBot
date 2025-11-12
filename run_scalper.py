from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict

from scalper.config import ScalperConfig, build_default_config
from scalper.runner import ScalperEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load_credentials() -> Dict[str, Dict[str, str]]:
    def read(prefix: str) -> Dict[str, str]:
        return {
            "api_key": os.environ.get(f"{prefix}_API_KEY", ""),
            "api_secret": os.environ.get(f"{prefix}_API_SECRET", ""),
            "passphrase": os.environ.get(f"{prefix}_API_PASSPHRASE", ""),
        }

    return {
        "coinbase": read("COINBASE"),
        "gemini": read("GEMINI"),
    }


async def main() -> None:
    creds = _load_credentials()
    config: ScalperConfig = build_default_config(creds)
    engine = ScalperEngine(config)
    await engine.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
