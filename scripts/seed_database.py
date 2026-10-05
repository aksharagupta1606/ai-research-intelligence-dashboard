import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.seed import seed_database


if __name__ == "__main__":
    count = seed_database()
    print(f"Added {count} demo papers.")