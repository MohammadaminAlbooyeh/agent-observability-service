"""Apply all database migrations (equivalent to `alembic upgrade head`)."""

from pathlib import Path

from alembic import command
from alembic.config import Config


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(cfg, "head")
    print("Database migrated to head.")


if __name__ == "__main__":
    main()
