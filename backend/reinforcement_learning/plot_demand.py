"""Plot held-out measured demand from the pinned SOFIE-derived intervals."""

from backend.configuration.paths import PROJECT_ROOT
from backend.reinforcement_learning.training_dataset import load_dataset


def main():
    import matplotlib.pyplot as plt

    data = load_dataset()
    slots = [slot for episode in data.test for slot in episode.slots]
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot([slot.source_time for slot in slots], [slot.observed_ev_kw for slot in slots])
    ax.set(
        xlabel="Recorded time (discontinuous accepted intervals)",
        ylabel="Observed EV demand (kW)",
    )
    ax.xaxis.set_major_locator(plt.MaxNLocator(6))
    fig.autofmt_xdate()
    destination = PROJECT_ROOT / "reports/figures/observed_ev_demand.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, bbox_inches="tight")
    print(destination)


if __name__ == "__main__":
    main()
