"""Inspect the validated intervals derived exclusively from the pinned SOFIE JSON."""

from backend.reinforcement_learning.training_dataset import load_dataset


def main():
    data = load_dataset()
    print(f"Source SHA-256: {data.source_sha256}")
    print(f"Train episodes: {len(data.train)}; test episodes: {len(data.test)}")
    print(f"Rejected intervals: {data.rejected_slots}")


if __name__ == "__main__":
    main()
