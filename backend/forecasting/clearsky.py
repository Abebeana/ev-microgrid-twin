"""Clear-sky plane-of-array irradiance and PVWatts AC power."""

from __future__ import annotations

from datetime import datetime

from backend.configuration.site import SiteConfig


def pvwatts_kw(moments: list[datetime], config: SiteConfig, nameplate_kw: float = 1.0) -> list[float]:
    """AC power for a nameplate array. Default nameplate is 1 kW so callers can scale it."""
    if not moments:
        return []
    pandas, pvlib = _libraries()
    times = pandas.DatetimeIndex(moments)
    if times.tz is None:
        times = times.tz_localize(config.site_timezone)
    location = pvlib.location.Location(
        config.latitude_deg,
        config.longitude_deg,
        tz=config.site_timezone,
        name=config.site_id,
    )
    position = location.get_solarposition(times)
    clearsky = location.get_clearsky(times, model="ineichen")
    irradiance = pvlib.irradiance.get_total_irradiance(
        config.pv_tilt_deg,
        config.pv_azimuth_deg,
        position["apparent_zenith"],
        position["azimuth"],
        clearsky["dni"],
        clearsky["ghi"],
        clearsky["dhi"],
    )
    dc_w = pvlib.pvsystem.pvwatts_dc(
        irradiance["poa_global"],
        25,
        nameplate_kw * 1000,
        -0.0035,
        25,
    )
    ac_w = pvlib.inverter.pvwatts(dc_w, nameplate_kw * 1000 * 1.1)
    return [round(max(float(value), 0) / 1000, 4) for value in ac_w]


def _libraries():
    import pandas
    import pvlib

    return pandas, pvlib
