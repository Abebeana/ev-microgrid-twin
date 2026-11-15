import { formatPower } from '@/shared/format/measurements'

import { useReplay } from '@/shared/state/replay-context'

import { SiteSummaryMetrics } from '@/features/telemetry/SiteSummaryMetrics'
import { TrendRangeControl } from '@/features/telemetry/TrendRangeControl'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'

import { TelemetryTrendChart } from '@/shared/charts/TelemetryTrendChart'

export function SolarProductionPage() {
  const { snapshot } = useReplay()
  return (
    <>
      <SiteSummaryMetrics />
      <div className="content-grid">
        <DataPanel title="Solar production" className="wide" action={<TrendRangeControl />}>
          <TelemetryTrendChart series={['solar_kw']} height={340} />
        </DataPanel>
        <DataPanel title="Now">
          <DetailList
            rows={[
              { label: 'Output', value: formatPower(snapshot.solar_kw) },
              { label: 'Samples', value: snapshot.solar_samples },
              { label: 'Forecast', value: '—' },
              { label: 'Weather', value: '—' },
            ]}
          />
        </DataPanel>
      </div>
    </>
  )
}
