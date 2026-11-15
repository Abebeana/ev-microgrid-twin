import { type BatteryModel } from '@/shared/api/contracts/studies'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { formatPercent, formatPower } from '@/shared/format/measurements'
import { rawAt } from '@/shared/format/time'
import { Button } from '@/shared/ui/button'
import { useQuery } from '@tanstack/react-query'

export function BatteryPhysicsPanel({ rawTime }: { rawTime: string }) {
  const model = useQuery({
    queryKey: ['battery-model', rawTime],
    queryFn: () =>
      getJson<BatteryModel>(`/api/battery/model?at=${encodeURIComponent(rawAt(rawTime))}`),
    enabled: Boolean(rawTime),
  })
  if (model.isError)
    return (
      <DataPanel title="Cell model" className="wide">
        <div className="load-error" role="alert">
          <strong>Cell model could not run.</strong>
          <p>{String(model.error)}</p>
          <Button className="action-button" onClick={() => model.refetch()}>
            Retry
          </Button>
        </div>
      </DataPanel>
    )
  if (!model.data)
    return (
      <DataPanel title="Cell model" className="wide">
        <div className="loading-state">Stepping the Thevenin pack…</div>
      </DataPanel>
    )
  const study = model.data
  return (
    <DataPanel title="Cell model" className="wide">
      <DetailList
        rows={[
          { label: 'Model', value: study.model },
          { label: 'Next step', value: `${study.direction} · ${study.minutes} min` },
          { label: 'Pack power', value: formatPower(study.pack_power_kw) },
          { label: 'Ending SoC', value: formatPercent(study.ending_soc_pct) },
          { label: 'Cell voltage', value: `${study.cell_voltage_v.toFixed(3)} V` },
          { label: 'Pack voltage', value: `${study.pack_voltage_v.toFixed(0)} V` },
          { label: 'Cell temperature', value: `${study.cell_temperature_c.toFixed(1)} °C` },
          {
            label: 'Pack build',
            value: `${study.series_cells}s${study.parallel_cells}p · ${study.modeled_pack_kwh} kWh`,
          },
          { label: 'Scaling', value: study.assumption },
        ]}
      />
    </DataPanel>
  )
}
