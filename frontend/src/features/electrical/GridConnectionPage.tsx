import { formatPercent, formatPower } from '@/shared/format/measurements'

import { useReplay } from '@/shared/state/replay-context'

import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { UnavailableState } from '@/shared/components/UnavailableState'

import { EnergyFlowDiagram } from '@/features/overview/EnergyFlowDiagram'

export function GridConnectionPage() {
  const { site, snapshot } = useReplay()
  return (
    <>
      <div className="content-grid">
        <DataPanel title="Grid" className="wide">
          <p className="quiet">
            <strong>No utility grid connection</strong>
          </p>
          <EnergyFlowDiagram />
        </DataPanel>
        <DataPanel title="Measured">
          <DetailList
            rows={[
              { label: 'PV', value: formatPower(snapshot.solar_kw) },
              {
                label: 'Battery SoC',
                value: formatPercent(snapshot.battery_soc_pct),
              },
              {
                label: 'EV load',
                value: formatPower(snapshot.observed_charging_kw),
              },
              {
                label: 'Storage',
                value: `${site.config.battery_capacity_kwh} kWh`,
              },
            ]}
          />
        </DataPanel>
        <DataPanel title="Missing" className="full">
          <div className="unavailable-grid">
            <UnavailableState title="Grid exchange" reason="No grid connection." />
            <UnavailableState title="Transformer" reason="No transformer signal in the source." />
            <UnavailableState title="Tariff" reason="No tariff in the source." />
          </div>
        </DataPanel>
      </div>
    </>
  )
}
