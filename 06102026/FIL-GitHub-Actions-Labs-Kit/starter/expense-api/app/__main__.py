"""Entry point: python -m app   (reads APP_* / JWT_* settings from the environment)."""
import sys

import uvicorn

from .config import ConfigError, load_settings
from .logging_utils import log_event


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:                     # A02: refuse to start, exit non-zero
        log_event("config_error", "ERROR", message=str(exc))
        return 1
    from .main import create_app
    app = create_app(settings)
    uvicorn.run(app, host="127.0.0.1", port=settings.port, server_header=False,
                access_log=False, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
