import { UnavailableState } from '@/shared/components/UnavailableState'
import { formatSiteTime } from '@/shared/format/time'
import { useReplay } from '@/shared/state/replay-context'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import ReactEChartsCore from 'echarts-for-react/esm/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

export function TelemetryTrendChart({
  series,
  height = 280,
}: {
  series: ('solar_kw' | 'observed_charging_kw' | 'battery_soc_pct')[]
  height?: number
}) {
  const { trend } = useReplay()
  const styles = getComputedStyle(document.documentElement)
  const color = (name: string) => styles.getPropertyValue(name).trim()
  const colors: Record<string, string> = {
    solar_kw: color('--accent'),
    observed_charging_kw: color('--green'),
    battery_soc_pct: color('--warn'),
  }
  const labels: Record<string, string> = {
    solar_kw: 'PV output · kW',
    observed_charging_kw: 'Observed charging · kW',
    battery_soc_pct: 'Battery SoC · %',
  }
  const hasPower = series.some((key) => key !== 'battery_soc_pct')
  const hasSoc = series.includes('battery_soc_pct')
  const axis = (unit: string, position: 'left' | 'right') => ({
    type: 'value',
    name: unit,
    position,
    nameTextStyle: { color: color('--text-muted') },
    axisLabel: { color: color('--text-muted') },
    splitLine: { lineStyle: { color: color('--chart-grid') } },
  })
  const option = {
    animation: false,
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: unknown) =>
        typeof value === 'number' ? value.toFixed(2) : 'Unavailable',
    },
    legend: { top: 0, textStyle: { color: color('--text-muted') } },
    grid: { left: 48, right: 24, top: 44, bottom: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trend.points.map((p) =>
        new Intl.DateTimeFormat('en-GB', {
          timeZone: 'Europe/Berlin',
          hour: '2-digit',
          minute: '2-digit',
        }).format(new Date(p.site_time)),
      ),
      axisLine: { lineStyle: { color: color('--border') } },
      axisLabel: { color: color('--text-muted'), hideOverlap: true },
    },
    yAxis:
      hasPower && hasSoc
        ? [axis('kW', 'left'), axis('%', 'right')]
        : [axis(hasSoc ? '%' : 'kW', 'left')],
    series: series.map((key) => ({
      name: labels[key],
      type: 'line',
      showSymbol: false,
      connectNulls: false,
      smooth: false,
      yAxisIndex: key === 'battery_soc_pct' && hasPower ? 1 : 0,
      lineStyle: { width: 2.5, color: colors[key] },
      itemStyle: { color: colors[key] },
      areaStyle: series.length === 1 ? { color: colors[key], opacity: 0.08 } : undefined,
      data: trend.points.map((p) => p[key]),
    })),
  }
  if (!trend.points.length)
    return (
      <UnavailableState
        title="No measurements in this range"
        reason="Choose another recorded time or range."
      />
    )
  return (
    <>
      <div
        role="img"
        aria-label={`Historical ${series.map((key) => labels[key]).join(' and ')} trend`}
      >
        <ReactEChartsCore echarts={echarts} option={option} style={{ height }} notMerge />
      </div>
      <details className="chart-data">
        <summary>View measured chart values</summary>
        <div className="table-scroll">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Site time</TableHead>
                {series.map((key) => (
                  <TableHead key={key}>{labels[key]}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {trend.points.map((point) => (
                <TableRow key={point.raw_time}>
                  <TableHead scope="row">{formatSiteTime(point.site_time)}</TableHead>
                  {series.map((key) => (
                    <TableCell key={key}>
                      {point[key] == null ? 'Unavailable' : point[key]?.toFixed(2)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </details>
    </>
  )
}
