import { type PhysicalForecast } from '@/shared/api/contracts/studies'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { formatPower } from '@/shared/format/measurements'
import { formatSiteTime, rawAt } from '@/shared/format/time'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useQuery } from '@tanstack/react-query'

const band = (row: PhysicalForecast['rows'][number]) =>
  row.lower_kw == null || row.upper_kw == null
    ? 'Not calibrated'
    : `${row.lower_kw.toFixed(2)} – ${row.upper_kw.toFixed(2)} kW`

export function PhysicalForecastPanel({ rawTime }: { rawTime: string }) {
  const forecast = useQuery({
    queryKey: ['physical-forecast', rawTime],
    queryFn: () =>
      getJson<PhysicalForecast>(`/api/forecasts/physical?at=${encodeURIComponent(rawAt(rawTime))}`),
    enabled: Boolean(rawTime),
  })
  if (forecast.isError)
    return (
      <DataPanel title="Physical PV" className="wide">
        <div className="load-error" role="alert">
          <strong>Physical forecast could not be calculated.</strong>
          <p>{String(forecast.error)}</p>
          <Button className="action-button" onClick={() => forecast.refetch()}>
            Retry
          </Button>
        </div>
      </DataPanel>
    )
  if (!forecast.data)
    return (
      <DataPanel title="Physical PV" className="wide">
        <div className="loading-state">Solving the clear-sky model…</div>
      </DataPanel>
    )
  const model = forecast.data
  return (
    <>
      <DataPanel title="Physical PV" className="wide">
        {!model.calibrated && (
          <p className="quiet">
            {model.training_samples} half-hour samples precede this minute. PVWatts is clipped at
            the nameplate until 24 samples can calibrate the scale.
          </p>
        )}
        <div className="table-scroll">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Horizon</TableHead>
                <TableHead>Site time</TableHead>
                <TableHead>PVWatts</TableHead>
                <TableHead>80% interval</TableHead>
                <TableHead>Recorded later</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {model.rows.map((row) => (
                <TableRow key={row.horizon_minutes}>
                  <TableHead scope="row">+{row.horizon_minutes} min</TableHead>
                  <TableCell>{formatSiteTime(row.site_time)}</TableCell>
                  <TableCell>{formatPower(row.clearsky_kw)}</TableCell>
                  <TableCell>{band(row)}</TableCell>
                  <TableCell>{formatPower(row.recorded_kw)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </DataPanel>
      <DataPanel title="Sky model">
        <DetailList
          rows={[
            { label: 'Method', value: 'Ineichen clear sky, PVWatts' },
            { label: 'Interval', value: model.calibrated ? 'MAPIE 80%' : 'Waiting for samples' },
            {
              label: 'Scale on 1 kW',
              value: model.scale_on_one_kw_array ?? '—',
            },
            { label: 'Clip', value: `${model.nameplate_clip_kw} kW` },
            { label: 'Place', value: model.location_assumption },
          ]}
        />
      </DataPanel>
    </>
  )
}
