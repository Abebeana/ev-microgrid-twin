import { Button } from '@/shared/ui/button'

import { ArrowRight, CircleCheck, Database, HardDrive } from 'lucide-react'

import { formatSiteTime } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'

import { MeasurementQualityTable } from './MeasurementQualityTable'

export function TelemetryPipelinePage() {
  const { quality, snapshot, site, navigate } = useReplay()
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'Microgrid minutes',
            value: Number(quality.metadata.microgrid_minutes).toLocaleString(),
            caption: 'Indexed derived samples',
          },
          {
            label: 'Wallbox minutes',
            value: Number(quality.metadata.charger_minutes).toLocaleString(),
            caption: 'Power.Active.Import · W → kW',
          },
          {
            label: 'Source wallboxes',
            value: String(site.wallboxes.length),
            caption: 'Discovered from charge_box',
          },
          {
            label: 'Mode',
            value: 'Replay + MQTT demo',
            caption: 'Historical values, simulated transport',
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Measurement path" className="wide">
          <div className="pipeline">
            <div>
              <Database size={22} />
              <strong>SOFIE JSON</strong>
              <small>Read-only · source hash recorded</small>
            </div>
            <ArrowRight size={18} />
            <div>
              <HardDrive size={22} />
              <strong>Derived replay store</strong>
              <small>1-minute aggregates, indexed events</small>
            </div>
            <ArrowRight size={18} />
            <div>
              <CircleCheck size={22} />
              <strong>Validated API</strong>
              <small>Units, coverage, provenance</small>
            </div>
          </div>
          <Button className="action-button" onClick={() => navigate('/stream')}>
            Watch simulated MQTT stream
          </Button>
        </DataPanel>
        <DataPanel title="Current sample">
          <DetailList
            rows={[
              { label: 'Recorded minute', value: snapshot.raw_time },
              { label: 'Site time', value: formatSiteTime(snapshot.site_time) },
              { label: 'PV samples', value: snapshot.solar_samples },
              {
                label: 'Charger coverage',
                value: `${snapshot.observed_wallboxes}/${snapshot.total_wallboxes}`,
              },
              {
                label: 'Missing PV',
                value: snapshot.solar_kw == null ? 'Unknown, not zero' : 'Measured',
              },
            ]}
          />
        </DataPanel>
        <DataPanel title="Quality checks" className="full">
          <MeasurementQualityTable />
        </DataPanel>
      </div>
    </>
  )
}
