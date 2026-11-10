# Telemetry exploration

`telemetry-exploration.ipynb` is a guided EDA of the pinned SOFIE export and its
validated replay CSV tables. It explains the source tables and field units, then
shows time coverage, solar and battery patterns, wallbox reporting, charging
sessions, connector events, and the limits of joint solar/EV comparisons. Charts
and explanations are saved in the notebook so it can be read without rerunning.

Run `make ingest` first if the replay CSV tables are absent. `make setup` installs
the notebook dependencies from the root `uv.lock`. For an existing environment,
run `uv sync --locked`, then select this project's `.venv` as the kernel. The notebook
locates the project from its current directory and checks source provenance before
reading replay tables.
