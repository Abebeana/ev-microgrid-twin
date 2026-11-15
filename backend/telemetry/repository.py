"""Read-only replay access and configuration provenance at the API boundary."""

from contextlib import contextmanager

from fastapi import HTTPException

from backend.configuration.dataset import derived_path
from backend.configuration.provenance import ingestion_fingerprint
from backend.configuration.site import load_site_config
from backend.storage.replay_reader import read_replay


@contextmanager
def replay_store():
    try:
        store = read_replay(derived_path())
        if store.metadata.get("ingestion_config_sha256") != ingestion_fingerprint(
            load_site_config()
        ):
            raise ValueError("Ingestion settings changed; rebuild the replay CSV files")
        yield store
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(503, f"Replay data is unavailable: {error}") from error


def metadata() -> dict[str, str]:
    with replay_store() as store:
        return dict(store.metadata)
