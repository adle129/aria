"""ARIA background worker entrypoint (R1-I02)."""

from app.services.worker_service import WorkerService


def main() -> None:
    WorkerService().run_forever()


if __name__ == "__main__":
    main()
