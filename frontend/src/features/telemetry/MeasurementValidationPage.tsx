import { Button } from '@/shared/ui/button'

import { useQuery } from '@tanstack/react-query'

import { ArrowRight } from 'lucide-react'

import { getJson } from '@/shared/api/http-client'

import { type BaselineForecast } from '@/shared/api/contracts/forecasting'
import { rawAt } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'

import { MeasurementQualityTable } from './MeasurementQualityTable'

export function MeasurementValidationPage() {
  const { quality, snapshot, site, rawTime, navigate } = useReplay()
  const baseline = useQuery({
    queryKey: ['baseline-forecast', rawTime],
    queryFn: () =>
      getJson<BaselineForecast>(`/api/forecasts/baseline?at=${encodeURIComponent(rawAt(rawTime))}`),
    enabled: Boolean(rawTime),
  })
  const coverage = quality.minutes.minutes
    ? (quality.minutes.solar_minutes / quality.minutes.minutes) * 100
    : 0
  const pvError = baseline.data?.rows[0]?.solar.validation.mae_kw
  const pairedOrigins = baseline.data?.rows[0]?.solar.validation.samples ?? 0
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'PV sample presence',
            value: `${coverage.toFixed(1)}%`,
            caption: 'All recorded minutes; nighttime nulls included',
          },
          {
            label: 'Battery SoC violations',
            value: String(quality.minutes.bad_soc),
            caption: 'Outside 0–100% in source',
          },
          {
            label: 'Wallboxes reporting now',
            value: `${snapshot.observed_wallboxes}/${snapshot.total_wallboxes}`,
            caption: 'Selected replay minute',
          },
          {
            label: 'PV baseline · 15 min MAE',
            value: baseline.isPending
              ? 'Calculating'
              : pvError == null
                ? 'Unavailable'
                : `${pvError.toFixed(2)} kW`,
            caption: baseline.isError
              ? 'Baseline check failed'
              : `${pairedOrigins} prior paired origins`,
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Validation evidence" className="wide">
          <MeasurementQualityTable />
          <Button className="action-button" onClick={() => navigate('/forecasts')}>
            Inspect baseline validation <ArrowRight size={14} />
          </Button>
        </DataPanel>
        <DataPanel title="Data provenance">
          <DetailList
            rows={[
              { label: 'Source file', value: quality.metadata.source_filename },
              {
                label: 'Source hash',
                value: <code className="hash">{quality.metadata.source_sha256}</code>,
              },
              {
                label: 'Raw time interpretation',
                value: site.config.source_timestamp_timezone,
              },
              { label: 'Site display time', value: site.config.site_timezone },
              {
                label: 'Source rows',
                value:
                  Number(quality.metadata.microgrid_minutes).toLocaleString() + ' derived minutes',
              },
            ]}
          />
        </DataPanel>
      </div>
    </>
  )
}
