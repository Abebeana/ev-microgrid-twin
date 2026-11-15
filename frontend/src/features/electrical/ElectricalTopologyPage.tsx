import { Button } from '@/shared/ui/button'

import { formatPower } from '@/shared/format/measurements'

import { useReplay } from '@/shared/state/replay-context'

import { PowerFlowPanel } from '@/features/electrical/PowerFlowPanel'
import { SiteSummaryMetrics } from '@/features/telemetry/SiteSummaryMetrics'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'

import { EnergyFlowDiagram } from '@/features/overview/EnergyFlowDiagram'

export function ElectricalTopologyPage() {
  const { snapshot, selectBox, site, rawTime } = useReplay()
  return (
    <>
      <SiteSummaryMetrics />
      <div className="content-grid">
        <DataPanel title="One-line" className="wide">
          <EnergyFlowDiagram />
          <div className="wallbox-links">
            {snapshot.wallboxes.map((box) => (
              <Button key={box.id} onClick={() => selectBox(box.id)}>
                {box.id}
                <span>{formatPower(box.power_kw)}</span>
              </Button>
            ))}
          </div>
        </DataPanel>
        <DataPanel title="Limits">
          <DetailList
            rows={[
              { label: 'Grid', value: 'None' },
              {
                label: 'Storage',
                value: `${site.config.battery_capacity_kwh} kWh`,
              },
              {
                label: 'Inverter max',
                value: `${site.config.battery_max_power_kw} kW`,
              },
              { label: 'Transformer', value: '—' },
            ]}
          />
        </DataPanel>
        <PowerFlowPanel rawTime={rawTime} />
      </div>
    </>
  )
}
