"""Wipe the database and reseed it from data/: uv run -m backend.seed"""

from backend.db import connect, seed

if __name__ == "__main__":
    with connect() as conn:
        counts = seed(conn)
    print("Seeded " + ", ".join(f"{count} {table}" for table, count in counts.items()))
