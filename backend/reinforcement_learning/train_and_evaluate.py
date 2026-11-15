"""Train on earlier SOFIE history and test on the last 30 recorded days."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.configuration.paths import PROJECT_ROOT
from backend.storage.atomic import write_json

from .evaluation import build_report
from .sac_policy import SacPolicy
from .training_dataset import DEFAULT_CONFIG, DEFAULT_REPLAY, load_dataset

DEFAULT_POLICY = PROJECT_ROOT / "models/battery_dispatch_sac.zip"
DEFAULT_REPORT = PROJECT_ROOT / "reports/reinforcement_learning/evaluation.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-dir", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--timesteps", type=int, default=40_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--now",
        type=datetime.fromisoformat,
        help="Optional timezone-aware simulated current time for reproducibility",
    )
    args = parser.parse_args()
    anchor = args.now or datetime.now(timezone.utc).replace(second=0, microsecond=0)
    if anchor.tzinfo is None:
        parser.error("--now must include a timezone offset")
    anchor = anchor.astimezone(timezone.utc)
    dataset = load_dataset(args.replay_dir, args.config)
    policy = SacPolicy.train(dataset.train, dataset.config, args.timesteps, args.seed)
    policy.save(
        args.policy,
        {
            "source_sha256": dataset.source_sha256,
            "training_before": dataset.test_first,
            "timesteps": args.timesteps,
            "seed": args.seed,
        },
    )
    restored = SacPolicy.load(args.policy)
    policy_hash = hashlib.sha256(args.policy.read_bytes()).hexdigest()
    report = build_report(dataset, restored, policy_hash, anchor, args.timesteps, args.seed)
    write_json(args.report, report)
    print(
        json.dumps(
            {
                "report": str(args.report),
                "policy": str(args.policy),
                "test_first": dataset.test_first,
                "test_last": dataset.test_last,
                "training_episodes": len(dataset.train),
                "test_episodes": len(dataset.test),
                "test_steps": report["experiment"]["test_steps"],
                "totals": report["totals"],
                "run_hash": report["run_hash"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
