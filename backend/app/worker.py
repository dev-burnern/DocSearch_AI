import logging
import time

from backend.app.core.config import get_settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    logging.getLogger("docsearch.worker").info(
        "worker scaffold started",
        extra={"queue_backend": settings.indexing_queue_backend},
    )

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
