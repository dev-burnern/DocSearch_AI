import logging
import time


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("docsearch.worker").info("worker scaffold started")

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
