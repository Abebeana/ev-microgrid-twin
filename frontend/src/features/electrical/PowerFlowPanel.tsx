import { type PowerFlow } from '@/shared/api/contracts/studies'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { formatPower } from '@/shared/format/measurements'
import { rawAt } from '@/shared/format/time'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useQuery } from '@tanstack/react-query'

export function PowerFlowPanel({ rawTime }: { rawTime: string }) {
  const flow = useQuery({
    queryKey: ['power-flow', rawTime],
    queryFn: () =>
      getJson<PowerFlow>(`/api/electrical/power-flow?at=${encodeURIComponent(rawAt(rawTime))}`),
    enabled: Boolean(rawTime),
  })
  if (flow.isError)
    return (
      <DataPanel title="Power flow" className="wide">
        <div className="load-error" role="alert">
          <strong>Power flow failed.</strong>
          <p>{String(flow.error)}</p>
          <Button className="action-button" onClick={() => flow.refetch()}>
            Retry
          </Button>
        </div>
      </DataPanel>
    )
  if (!flow.data)
    return (
      <DataPanel title="Power flow" className="wide">
        <div className="loading-state">Solving the feeder model…</div>
      </DataPanel>
    )
  const study = flow.data
  if (!study.converged)
    return (
      <DataPanel title="Power flow" className="wide">
        <p className="quiet">{study.reason}</p>
      </DataPanel>
    )
  return (
    <>
      <DataPanel title="Power flow" className="wide">
        <div className="table-scroll">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Bus</TableHead>
                <TableHead>Voltage</TableHead>
                <TableHead>Angle</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {study.buses?.map((bus) => (
                <TableRow key={bus.name}>
                  <TableHead scope="row">{bus.name}</TableHead>
                  <TableCell>{bus.voltage_pu.toFixed(3)} pu</TableCell>
                  <TableCell>{bus.angle_deg.toFixed(2)}°</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </DataPanel>
      <DataPanel title="Inverter slack">
        <DetailList
          rows={[
            { label: 'Inverter power', value: formatPower(study.inverter_kw) },
            {
              label: 'Reactive',
              value:
                study.inverter_kvar == null ? 'Unavailable' : `${study.inverter_kvar.toFixed(2)} kVAr`,
            },
            { label: 'Losses', value: formatPower(study.losses_kw) },
            {
              label: 'Lowest voltage',
              value: `${study.minimum_voltage_pu?.toFixed(3)} pu`,
            },
            {
              label: 'Heaviest feeder',
              value: `${study.maximum_feeder_loading_pct?.toFixed(1)}%`,
            },
            {
              label: 'Unmeasured chargers',
              value: study.unmeasured_chargers?.length
                ? study.unmeasured_chargers.join(', ')
                : 'None',
            },
            { label: 'Forming source', value: study.forming_source ?? '' },
          ]}
        />
      </DataPanel>
    </>
  )
}
