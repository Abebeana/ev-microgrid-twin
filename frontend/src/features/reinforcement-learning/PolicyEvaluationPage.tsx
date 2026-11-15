import {
  type DispatchPolicyMethod,
  type PolicyEvaluationReport,
} from '@/shared/api/contracts/policy-evaluation'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'
import { UnavailableState } from '@/shared/components/UnavailableState'
import { Button } from '@/shared/ui/button'
import { Label } from '@/shared/ui/label'
import { NativeSelect } from '@/shared/ui/native-select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useQuery } from '@tanstack/react-query'
import ReactEChartsCore from 'echarts-for-react/esm/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useState } from 'react'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const methods: { key: DispatchPolicyMethod; label: string; detail: string }[] = [
  { key: 'idle', label: 'No dispatch', detail: 'Battery stays idle' },
  {
    key: 'greedy',
    label: 'Simple rule',
    detail: 'Charge on PV surplus; discharge on EV deficit',
  },
  {
    key: 'rl',
    label: 'Soft Actor-Critic',
    detail: 'Continuous battery power, trained on earlier days',
  },
  {
    key: 'oracle',
    label: 'Lookahead bound',
    detail: 'Sees the full test episode in advance',
  },
]

const energy = (value: number) => `${value.toFixed(2)} kWh`
const clock = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })

export function PolicyEvaluationPage() {
  const report = useQuery({
    queryKey: ['rl-experiment'],
    queryFn: () => getJson<PolicyEvaluationReport>('/api/rl/experiment'),
  })
  const [day, setDay] = useState('')
  if (report.isError)
    return (
      <UnavailableState
        title="RL experiment unavailable"
        reason={String(report.error)}
        action={
          <Button className="secondary-button" onClick={() => report.refetch()}>
            Retry
          </Button>
        }
      />
    )
  if (!report.data)
    return <div className="loading-state">Loading the Soft Actor-Critic evaluation…</div>
  const data = report.data
  const selectedDay = day || data.daily.at(-1)?.source_day || ''
  const points = data.points.filter((point) => point.source_time.startsWith(selectedDay))
  const dayTotals = data.daily.find((row) => row.source_day === selectedDay)?.methods
  const gap = data.totals.rl.unserved_ev_kwh - data.totals.greedy.unserved_ev_kwh
  const gapPct = data.totals.greedy.unserved_ev_kwh
    ? (gap / data.totals.greedy.unserved_ev_kwh) * 100
    : 0
  const styles = getComputedStyle(document.documentElement)
  const color = (name: string) => styles.getPropertyValue(name).trim()
  const option = {
    animation: false,
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: unknown) =>
        typeof value === 'number' ? `${value.toFixed(2)} kW` : 'Unavailable',
    },
    legend: { top: 0, textStyle: { color: color('--text-muted') } },
    grid: { left: 48, right: 20, top: 48, bottom: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((point) => point.source_time.slice(11)),
      axisLine: { lineStyle: { color: color('--border') } },
      axisLabel: { color: color('--text-muted'), hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      name: 'kW',
      nameTextStyle: { color: color('--text-muted') },
      axisLabel: { color: color('--text-muted') },
      splitLine: { lineStyle: { color: color('--chart-grid') } },
    },
    series: [
      {
        name: 'PV measured',
        type: 'line',
        showSymbol: false,
        data: points.map((point) => point.solar_kw),
        lineStyle: { color: color('--accent'), width: 2.3 },
        itemStyle: { color: color('--accent') },
      },
      {
        name: 'EV observed',
        type: 'line',
        showSymbol: false,
        data: points.map((point) => point.observed_ev_kw),
        lineStyle: { color: color('--warn'), width: 2.3 },
        itemStyle: { color: color('--warn') },
      },
      {
        name: 'SAC battery',
        type: 'line',
        showSymbol: false,
        data: points.map((point) => point.outcomes.rl.battery_kw),
        lineStyle: { color: color('--green'), width: 2.3 },
        itemStyle: { color: color('--green') },
      },
    ],
  }
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'SAC · unserved EV',
            value: energy(data.totals.rl.unserved_ev_kwh),
            caption: 'Modeled observed EV subset',
          },
          {
            label: 'Simple rule · unserved EV',
            value: energy(data.totals.greedy.unserved_ev_kwh),
            caption: 'Same test intervals and starting SoC',
          },
          {
            label: 'RL minus simple rule',
            value: `${gap >= 0 ? '+' : ''}${gapPct.toFixed(1)}%`,
            caption: 'Lower unserved energy is better',
          },
          {
            label: 'Held-out test',
            value: `${data.experiment.test_steps} intervals`,
            caption: `${data.source.test_days} recorded days · ${data.experiment.test_episodes} episodes`,
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="What the test found" className="wide">
          <p className="quiet">
            {gap > 0.01
              ? `The simple rule served ${energy(gap)} more observed EV demand than the learned policy.`
              : gap < -0.01
                ? `The learned policy served ${energy(-gap)} more observed EV demand than the simple rule.`
                : 'The learned policy and simple rule served the same observed EV demand.'}
          </p>
          <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Dispatch method</TableHead>
                  <TableHead>Unserved EV</TableHead>
                  <TableHead>PV curtailed</TableHead>
                  <TableHead>Battery throughput</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {methods.map((method) => (
                  <TableRow key={method.key}>
                    <TableHead scope="row">
                      {method.label}
                      <small className="rl-method-detail">{method.detail}</small>
                    </TableHead>
                    <TableCell>{energy(data.totals[method.key].unserved_ev_kwh)}</TableCell>
                    <TableCell>{energy(data.totals[method.key].curtailed_pv_kwh)}</TableCell>
                    <TableCell>{energy(data.totals[method.key].battery_throughput_kwh)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="small-note">
            No battery commands were sent. Coverage floor {data.experiment.minimum_coverage_pct}%.
          </p>
        </DataPanel>
        <DataPanel title="Experiment contract">
          <DetailList
            rows={[
              {
                label: 'Source test window',
                value: `${data.source.test_first} to ${data.source.test_last}`,
              },
              {
                label: 'Simulated current',
                value: clock(data.source.simulated_current_at),
              },
              {
                label: 'Training',
                value: `${data.experiment.training_episodes} earlier episodes · ${data.experiment.training_iterations.toLocaleString()} environment steps`,
              },
              {
                label: 'Algorithm',
                value: data.experiment.algorithm.replaceAll('_', ' '),
              },
              {
                label: 'Battery',
                value: `${data.experiment.battery_capacity_kwh} kWh · ${data.experiment.battery_max_power_kw} kW · ${data.experiment.battery_min_soc_pct}% reserve`,
              },
              {
                label: 'SOFIE source SHA-256',
                value: <code className="hash">{data.source.sha256}</code>,
              },
              {
                label: 'Run hash',
                value: <code className="hash">{data.run_hash}</code>,
              },
            ]}
          />
        </DataPanel>
        <DataPanel
          title="Replay a test day"
          className="full"
          action={
            <div className="rl-day-selector">
              <Label htmlFor="rl-day">Recorded day</Label>
              <NativeSelect
                id="rl-day"
                value={selectedDay}
                onChange={(event) => setDay(event.target.value)}
              >
                {data.daily.map((row) => (
                  <option key={row.source_day} value={row.source_day}>
                    {row.source_day}
                  </option>
                ))}
              </NativeSelect>
            </div>
          }
        >
          {points.length ? (
            <>
              <div
                role="img"
                aria-label={`Measured PV, observed EV charging, and RL battery dispatch on ${selectedDay}`}
              >
                <ReactEChartsCore
                  echarts={echarts}
                  option={option}
                  style={{ height: 310 }}
                  notMerge
                />
              </div>
              <div className="table-scroll rl-replay-table">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Recorded source</TableHead>
                      <TableHead>Simulated clock</TableHead>
                      <TableHead>PV</TableHead>
                      <TableHead>EV</TableHead>
                      <TableHead>RL battery</TableHead>
                      <TableHead>RL unserved</TableHead>
                      <TableHead>Reporting wallboxes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {points.map((point) => (
                      <TableRow key={point.source_time}>
                        <TableHead scope="row">{point.source_time}</TableHead>
                        <TableCell>{clock(point.simulated_at)}</TableCell>
                        <TableCell>{point.solar_kw.toFixed(2)} kW</TableCell>
                        <TableCell>{point.observed_ev_kw.toFixed(2)} kW</TableCell>
                        <TableCell>{point.outcomes.rl.battery_kw.toFixed(2)} kW</TableCell>
                        <TableCell>{point.outcomes.rl.unserved_ev_kwh.toFixed(3)} kWh</TableCell>
                        <TableCell>at least {point.minimum_reporting_wallboxes}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </>
          ) : (
            <UnavailableState title="No tested intervals" reason="Choose another recorded day." />
          )}
          {dayTotals && (
            <p className="small-note">
              {selectedDay}: RL {energy(dayTotals.rl.unserved_ev_kwh)} unserved · rule{' '}
              {energy(dayTotals.greedy.unserved_ev_kwh)} unserved.
            </p>
          )}
        </DataPanel>
      </div>
    </>
  )
}
