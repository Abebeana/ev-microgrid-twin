import { MicrogridScene } from '@/features/site/components/MicrogridScene'
import type { SiteView } from '@/features/site/scene-model'
import { stateOf, stateText } from '@/features/site/scene-model'
import { SiteTelemetryTrend } from '@/features/site/SiteTelemetryTrend'
import { formatPercent, formatPower } from '@/shared/format/measurements'
import { formatSiteTime } from '@/shared/format/time'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { useIsFetching } from '@tanstack/react-query'
import { BatteryCharging, Focus, Sun } from 'lucide-react'
import { useState } from 'react'
import './site-scene.css'

export function SiteScenePage() {
  const { snapshot, site, trend, selectBox, hours, setHours } = useReplay()
  const [view, setView] = useState<SiteView>('overview')
  const [xray, setXray] = useState(true)
  const updating = useIsFetching({ queryKey: ['replay'] }) > 0
  const boxes = snapshot.wallboxes
  const selected = boxes.find((box) => box.id === view)
  return (
    <div className="site-work">
      <section className="site-stage" aria-label="EV charging station">
        <MicrogridScene
          boxes={boxes}
          solar={snapshot.solar_kw}
          soc={snapshot.battery_soc_pct}
          view={view}
          choose={setView}
          xray={xray}
        />
        <div className="site-stage-bar">
          <div className="site-view-controls" role="group" aria-label="Camera">
            <Button aria-pressed={view === 'overview'} onClick={() => setView('overview')}>
              Overview
            </Button>
            <Button aria-pressed={view === 'solar'} onClick={() => setView('solar')}>
              <Sun size={14} /> Solar
            </Button>
            <Button aria-pressed={view === 'battery'} onClick={() => setView('battery')}>
              <BatteryCharging size={14} /> Storage
            </Button>
            <Button aria-pressed={xray} onClick={() => setXray(!xray)}>
              <Focus size={14} /> X-ray
            </Button>
          </div>
          {updating && (
            <span className="site-updating" role="status">
              Updating
            </span>
          )}
          <div className="site-readout">
            <span>
              PV <strong>{formatPower(snapshot.solar_kw)}</strong>
            </span>
            <span>
              EV <strong>{formatPower(snapshot.observed_charging_kw)}</strong>
            </span>
            <span>
              SoC <strong>{formatPercent(snapshot.battery_soc_pct)}</strong>
            </span>
            <span>
              Chargers{' '}
              <strong>
                {snapshot.observed_wallboxes}/{snapshot.total_wallboxes}
              </strong>
            </span>
          </div>
        </div>
      </section>
      <div className="site-split">
        <div className="site-bays">
          {boxes.map((box) => (
            <Button
              key={box.id}
              className={view === box.id ? 'selected' : ''}
              aria-pressed={view === box.id}
              onClick={() => setView(box.id)}
            >
              <i className={stateOf(box)} />
              <span>{box.id}</span>
              <strong>
                {box.power_kw == null ? '—' : box.power_kw.toFixed(2)}
                <small> kW</small>
              </strong>
              <small>{stateText(box)}</small>
            </Button>
          ))}
        </div>
        <aside className="site-inspector">
          {selected ? (
            <>
              <h2>{selected.id}</h2>
              <div className="site-inspector-power">{formatPower(selected.power_kw)}</div>
              <span className={'site-inspector-state ' + stateOf(selected)}>
                {stateText(selected)}
              </span>
              <dl>
                <div>
                  <dt>Vendor</dt>
                  <dd>{selected.vendor ?? '—'}</dd>
                </div>
                <div>
                  <dt>Model</dt>
                  <dd>{selected.model ?? '—'}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{selected.status_stale ? selected.status + ' · stale' : selected.status}</dd>
                </div>
                <div>
                  <dt>Power sample</dt>
                  <dd>{formatSiteTime(selected.power_site_time)}</dd>
                </div>
                <div>
                  <dt>Samples</dt>
                  <dd>{selected.power_sample_count}</dd>
                </div>
                <div>
                  <dt>Error</dt>
                  <dd>
                    {selected.error_code && selected.error_code !== 'NoError'
                      ? selected.error_code
                      : '—'}
                  </dd>
                </div>
              </dl>
              <Button className="site-inspect-link" onClick={() => selectBox(selected.id)}>
                Inspect
              </Button>
            </>
          ) : view === 'battery' ? (
            <>
              <h2>Storage</h2>
              <div className="site-inspector-power">{formatPercent(snapshot.battery_soc_pct)}</div>
              <dl>
                <div>
                  <dt>Temperature</dt>
                  <dd>
                    {snapshot.battery_temp_c == null
                      ? '—'
                      : snapshot.battery_temp_c.toFixed(1) + ' °C'}
                  </dd>
                </div>
                <div>
                  <dt>Capacity</dt>
                  <dd>{site.config.battery_capacity_kwh} kWh</dd>
                </div>
                <div>
                  <dt>Max power</dt>
                  <dd>{site.config.battery_max_power_kw} kW</dd>
                </div>
              </dl>
            </>
          ) : view === 'solar' ? (
            <>
              <h2>Solar</h2>
              <div className="site-inspector-power">{formatPower(snapshot.solar_kw)}</div>
              <dl>
                <div>
                  <dt>Samples</dt>
                  <dd>{snapshot.solar_samples}</dd>
                </div>
                <div>
                  <dt>Recorded</dt>
                  <dd>{formatSiteTime(snapshot.site_time)}</dd>
                </div>
              </dl>
            </>
          ) : (
            <>
              <h2>Station</h2>
              <div className="site-inspector-power">
                {snapshot.active_sessions}
                <small> sessions</small>
              </div>
              <dl>
                <div>
                  <dt>Reporting</dt>
                  <dd>
                    {snapshot.observed_wallboxes}/{snapshot.total_wallboxes}
                  </dd>
                </div>
                <div>
                  <dt>PV samples</dt>
                  <dd>{snapshot.solar_samples}</dd>
                </div>
              </dl>
            </>
          )}
        </aside>
      </div>
      <section className="site-trend-section">
        <div className="site-range" role="group" aria-label="Trend range">
          {[6, 24, 72].map((value) => (
            <Button key={value} aria-pressed={hours === value} onClick={() => setHours(value)}>
              {value}h
            </Button>
          ))}
        </div>
        {trend.points.length ? <SiteTelemetryTrend /> : <p>No measurements.</p>}
      </section>
    </div>
  )
}
