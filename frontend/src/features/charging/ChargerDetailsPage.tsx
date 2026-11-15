import { Label } from '@/shared/ui/label'

import { NativeSelect } from '@/shared/ui/native-select'

import { useQuery } from '@tanstack/react-query'

import { getJson } from '@/shared/api/http-client'

import { formatPower } from '@/shared/format/measurements'
import { formatSiteTime, rawAt } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { TrendRangeControl } from '@/features/telemetry/TrendRangeControl'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { UnavailableState } from '@/shared/components/UnavailableState'

import { ChargingSessionTable } from './ChargingSessionTable'

export function ChargerDetailsPage() {
  const { snapshot, selectedBox, rawTime, hours, sessions, selectBox } = useReplay()
  const box = snapshot.wallboxes.find((item) => item.id === selectedBox) ?? snapshot.wallboxes[0]
  const history = useQuery({
    queryKey: ['charger-trend', box?.id, rawTime, hours],
    queryFn: () =>
      getJson<
        {
          raw_time: string
          site_time: string
          power_kw: number
          observed_minutes: number
        }[]
      >(`/api/chargers/${box.id}/trend?at=${encodeURIComponent(rawAt(rawTime))}&hours=${hours}`),
    enabled: Boolean(box),
  })
  if (!box)
    return (
      <UnavailableState
        title="No wallbox configured"
        reason="The source contains no wallbox assets."
      />
    )
  return (
    <>
      <div className="inspection-select">
        <Label htmlFor="inspection-box">Inspect wallbox</Label>
        <NativeSelect
          id="inspection-box"
          value={box.id}
          onChange={(event) => selectBox(event.target.value)}
        >
          {snapshot.wallboxes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.id}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="content-grid">
        <DataPanel title={`${box.id} · recorded state`} className="wide">
          <div className="inspection-hero">
            <div>
              <span>Measured power</span>
              <strong>{formatPower(box.power_kw)}</strong>
            </div>
            <div>
              <span>Last OCPP status</span>
              <strong>
                {box.status}
                {box.status_stale ? ' · old event' : ''}
              </strong>
            </div>
            <div>
              <span>Error code</span>
              <strong>{box.error_code ?? 'None recorded'}</strong>
            </div>
          </div>
          <div className="panel-subtitle">
            Power history <TrendRangeControl />
          </div>
          {history.isError ? (
            <p className="error-text">{String(history.error)}</p>
          ) : (
            <MiniPowerChart rows={history.data ?? []} />
          )}
        </DataPanel>
        <DataPanel title="Asset details">
          <DetailList
            rows={[
              { label: 'Vendor', value: box.vendor ?? 'Unavailable' },
              { label: 'Model', value: box.model ?? 'Unavailable' },
              { label: 'Firmware', value: box.firmware ?? 'Unavailable' },
              {
                label: 'Last power sample',
                value: formatSiteTime(box.power_site_time),
              },
              {
                label: 'Last status event',
                value: formatSiteTime(box.status_site_time),
              },
            ]}
          />
        </DataPanel>
        <DataPanel title="Sessions on this wallbox" className="full">
          <ChargingSessionTable rows={sessions.filter((row) => row.wallbox_id === box.id)} />
        </DataPanel>
      </div>
    </>
  )
}

function MiniPowerChart({ rows }: { rows: { site_time: string; power_kw: number }[] }) {
  if (!rows.length)
    return (
      <UnavailableState
        title="No charger readings"
        reason="Choose another replay time to inspect this wallbox."
      />
    )
  const max = Math.max(...rows.map((row) => row.power_kw), 1)
  return (
    <div className="mini-bars" role="img" aria-label="Recorded wallbox power over selected range">
      {rows.map((row, index) => (
        <div
          key={index}
          title={`${formatSiteTime(row.site_time)} · ${formatPower(row.power_kw)}`}
          style={{ height: `${Math.max(2, (row.power_kw / max) * 100)}%` }}
        />
      ))}
    </div>
  )
}
