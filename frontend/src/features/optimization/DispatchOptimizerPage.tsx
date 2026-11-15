import { type ScenarioResult } from '@/shared/api/contracts/scenarios'
import { postJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'
import { UnavailableState } from '@/shared/components/UnavailableState'
import { formatSiteTime, rawAt } from '@/shared/format/time'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'

function resultMetrics(result: ScenarioResult) {
  return [
    {
      label: 'Unserved observed EV energy',
      value: `${result.totals.unserved_ev_kwh.toFixed(2)} kWh`,
      caption: 'Modeled; not measured',
    },
    {
      label: 'PV curtailment',
      value: `${result.totals.curtailed_pv_kwh.toFixed(2)} kWh`,
      caption: 'Modeled what-if',
    },
    {
      label: 'Battery discharge',
      value: `${result.totals.battery_discharge_kwh.toFixed(2)} kWh`,
      caption: 'Advisory schedule',
    },
    {
      label: 'Without dispatch',
      value: `${result.totals.baseline_without_dispatch_unserved_ev_kwh.toFixed(2)} kWh`,
      caption: 'Same observed EV/PV subset',
    },
  ]
}

function Schedule({ result }: { result: ScenarioResult }) {
  return (
    <div className="table-scroll">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Site time</TableHead>
            <TableHead>PV</TableHead>
            <TableHead>Observed EV</TableHead>
            <TableHead>Battery charge</TableHead>
            <TableHead>Battery discharge</TableHead>
            <TableHead>Unserved EV</TableHead>
            <TableHead>Ending SoC</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {result.schedule.map((row) => (
            <TableRow key={row.raw_time}>
              <TableCell>{formatSiteTime(row.site_time)}</TableCell>
              <TableCell>{row.solar_kw.toFixed(2)} kW</TableCell>
              <TableCell>{row.observed_charging_kw.toFixed(2)} kW</TableCell>
              <TableCell>{row.battery_charge_kw.toFixed(2)} kW</TableCell>
              <TableCell>{row.battery_discharge_kw.toFixed(2)} kW</TableCell>
              <TableCell>{row.unserved_ev_kw.toFixed(2)} kW</TableCell>
              <TableCell>{row.ending_soc_pct.toFixed(1)}%</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export function DispatchOptimizerPage() {
  const { rawTime, scenarioA, setScenarioA, navigate, site, availability } = useReplay()
  const step = site.config.optimizer_step_minutes
  const alignedTime =
    rawTime.slice(0, 14) +
    String(Math.floor(Number(rawTime.slice(14, 16)) / step) * step).padStart(2, '0')
  const run = useMutation({
    mutationFn: () =>
      postJson<ScenarioResult>('/api/scenarios/evaluate', {
        start: rawAt(alignedTime),
        hours: 1,
        charging_multiplier: 1,
        solar_multiplier: 1,
        battery_capacity_kwh: null,
        outage_wallbox_id: null,
      }),
    onSuccess: setScenarioA,
  })
  return (
    <>
      <MetricStrip
        items={
          scenarioA
            ? resultMetrics(scenarioA)
            : [
                {
                  label: 'Operating mode',
                  value: 'Islanded',
                  caption: 'No grid import in the model',
                },
                {
                  label: 'Battery capacity',
                  value: `${site.config.battery_capacity_kwh} kWh`,
                  caption: 'Configured from SOFIE description',
                },
                {
                  label: 'Inverter maximum',
                  value: `${site.config.battery_max_power_kw} kW`,
                  caption: 'Configured from SOFIE description',
                },
                {
                  label: 'Control state',
                  value: 'Advisory',
                  caption: availability.control.reason,
                },
              ]
        }
      />
      <div className="content-grid">
        <DataPanel title="Dispatch optimizer" className="wide">
          {scenarioA ? (
            <>
              <Schedule result={scenarioA} />
              <div className="hash-line">
                Reproducibility hash <code>{scenarioA.run_hash}</code>
              </div>
            </>
          ) : (
            <UnavailableState
              title="No advisory run selected"
              reason="Run a one-hour historical replay at the selected recorded time. Forecast-driven dispatch remains unavailable."
              action={
                <Button
                  className="action-button"
                  onClick={() => run.mutate()}
                  disabled={run.isPending}
                >
                  Run historical advisory
                </Button>
              }
            />
          )}
          {run.isError && (
            <p role="alert" className="error-text">
              {String(run.error)}
            </p>
          )}
        </DataPanel>
        <DataPanel title="Model constraints">
          <DetailList
            rows={[
              { label: 'Grid exchange', value: 'None · islanded' },
              {
                label: 'SoC reserve',
                value: `${site.config.battery_min_soc_pct}%`,
              },
              {
                label: 'Battery power limit',
                value: `${site.config.battery_max_power_kw} kW`,
              },
              {
                label: 'Round-trip efficiency',
                value: `${(site.config.battery_model_efficiency * 100).toFixed(0)}% assumed`,
              },
              { label: 'Formulation', value: 'MILP · charge or discharge' },
              { label: 'Interval', value: `${step} minutes` },
              {
                label: 'Measurement coverage floor',
                value: `${site.config.optimizer_min_coverage_pct}%`,
              },
              { label: 'Control integration', value: 'Unavailable' },
            ]}
          />
          <Button className="action-button" onClick={() => navigate('/scenarios')}>
            Edit scenario inputs <ArrowRight size={14} />
          </Button>
        </DataPanel>
        {scenarioA && (
          <DataPanel title="Record" className="full">
            <pre className="provenance">{JSON.stringify(scenarioA.provenance, null, 2)}</pre>
          </DataPanel>
        )}
      </div>
    </>
  )
}
