from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict

from scalper.config import ScalperConfig, build_default_config
from scalper.runner import ScalperEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load_credentials() -> Dict[str, Dict[str, str]]:
    def pick(*names: str) -> str:
        for name in names:
            value = os.environ.get(name)
            if value:
                return value.strip()
        return ""

    def read(prefix: str) -> Dict[str, str]:
        return {
            "api_key": pick(f"{prefix}_API_KEY", f"{prefix}_KEY", f"{prefix}KEY"),
            "api_secret": pick(f"{prefix}_API_SECRET", f"{prefix}_SECRET", f"{prefix}SECRET"),
            "passphrase": pick(
                f"{prefix}_API_PASSPHRASE",
                f"{prefix}_PASSPHRASE",
                f"{prefix}_PASSWORD",
                f"{prefix}_API_PASSWORD",
            ),
        }

    return {
        "coinbase": read("COINBASE"),
        "gemini": read("GEMINI"),
    }


async def main() -> None:
    creds = _load_credentials()
    config: ScalperConfig = build_default_config(creds)
    for venue, info in creds.items():
        masked_key = "set" if info.get("api_key") else "missing"
        masked_secret = "set" if info.get("api_secret") else "missing"
        logging.info("[STARTUP] %s credentials key=%s secret=%s", venue.upper(), masked_key, masked_secret)
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
