import { PhysicalForecastPanel } from '@/features/forecasting/PhysicalForecastPanel'
import { type BaselineForecast } from '@/shared/api/contracts/forecasting'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'
import { UnavailableState } from '@/shared/components/UnavailableState'
import { formatPower } from '@/shared/format/measurements'
import { formatSiteTime, rawAt } from '@/shared/format/time'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useQuery } from '@tanstack/react-query'

const errorLabel = (value: number | null) =>
  value == null ? 'Not enough paired samples' : `${value.toFixed(2)} kW`

export function ForecastsPage() {
  const { rawTime } = useReplay()
  const forecast = useQuery({
    queryKey: ['baseline-forecast', rawTime],
    queryFn: () =>
      getJson<BaselineForecast>(`/api/forecasts/baseline?at=${encodeURIComponent(rawAt(rawTime))}`),
    enabled: Boolean(rawTime),
  })
  if (forecast.isError)
    return (
      <div className="load-error" role="alert">
        <strong>Baseline could not be calculated.</strong>
        <p>{String(forecast.error)}</p>
        <Button className="action-button" onClick={() => forecast.refetch()}>
          Retry
        </Button>
      </div>
    )
  if (!forecast.data)
    return <div className="loading-state">Calculating a recorded-data baseline…</div>
  const model = forecast.data
  const first = model.rows[0]
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'PV · 15 min estimate',
            value: formatPower(first.solar.predicted_kw),
            caption: 'Selected minute held constant',
          },
          {
            label: 'EV · 15 min estimate',
            value: formatPower(first.observed_ev.predicted_kw),
            caption: `Requires all ${model.wallboxes_required} wallboxes`,
          },
          {
            label: 'PV backtest MAE',
            value: errorLabel(first.solar.validation.mae_kw),
            caption: `${first.solar.validation.samples} paired origins · 15 min`,
          },
          {
            label: 'EV backtest MAE',
            value: errorLabel(first.observed_ev.validation.mae_kw),
            caption: `${first.observed_ev.validation.samples} paired origins · 15 min`,
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Baseline" className="wide">
          {first.solar.predicted_kw == null && first.observed_ev.predicted_kw == null ? (
            <UnavailableState
              title="No baseline"
              reason="PV or complete wallbox power is missing at this time."
            />
          ) : (
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Horizon</TableHead>
                    <TableHead>Site time</TableHead>
                    <TableHead>PV estimate</TableHead>
                    <TableHead>PV recorded</TableHead>
                    <TableHead>EV estimate</TableHead>
                    <TableHead>EV recorded</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {model.rows.map((row) => (
                    <TableRow key={row.horizon_minutes}>
                      <TableHead scope="row">+{row.horizon_minutes} min</TableHead>
                      <TableCell>{formatSiteTime(row.site_time)}</TableCell>
                      <TableCell>{formatPower(row.solar.predicted_kw)}</TableCell>
                      <TableCell>{formatPower(row.solar.recorded_kw)}</TableCell>
                      <TableCell>{formatPower(row.observed_ev.predicted_kw)}</TableCell>
                      <TableCell>{formatPower(row.observed_ev.recorded_kw)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </DataPanel>
        <DataPanel title="Inputs">
          <DetailList
            rows={[
              {
                label: 'Origin',
                value: formatSiteTime(model.origin_site_time),
              },
              { label: 'Source clock', value: model.origin_raw },
              { label: 'Method', value: model.model },
              { label: 'PV', value: 'Observed at origin' },
              {
                label: 'EV',
                value: `All ${model.wallboxes_required} wallboxes`,
              },
              {
                label: 'Source hash',
                value: <code className="hash">{model.source_sha256}</code>,
              },
            ]}
          />
        </DataPanel>
        <DataPanel title="Error" className="wide">
          <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Horizon</TableHead>
                  <TableHead>PV MAE</TableHead>
                  <TableHead>PV 80th abs. error</TableHead>
                  <TableHead>EV MAE</TableHead>
                  <TableHead>EV 80th abs. error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {model.rows.map((row) => (
                  <TableRow key={row.horizon_minutes}>
                    <TableHead scope="row">{row.horizon_minutes} min</TableHead>
                    <TableCell>{errorLabel(row.solar.validation.mae_kw)}</TableCell>
                    <TableCell>{errorLabel(row.solar.validation.p80_absolute_error_kw)}</TableCell>
                    <TableCell>{errorLabel(row.observed_ev.validation.mae_kw)}</TableCell>
                    <TableCell>
                      {errorLabel(row.observed_ev.validation.p80_absolute_error_kw)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DataPanel>
        <PhysicalForecastPanel rawTime={rawTime} />
      </div>
    </>
  )
}
