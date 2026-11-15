import { type OcppRegistry } from '@/shared/api/contracts/studies'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { UnavailableState } from '@/shared/components/UnavailableState'
import { formatPower } from '@/shared/format/measurements'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useQuery } from '@tanstack/react-query'

export function OcppSessionsPanel() {
  const registry = useQuery({
    queryKey: ['ocpp-charge-points'],
    queryFn: () => getJson<OcppRegistry>('/api/chargers/ocpp'),
    refetchInterval: 5000,
  })
  if (registry.isError)
    return (
      <DataPanel title="OCPP charge points" className="full">
        <div className="load-error" role="alert">
          <strong>OCPP registry could not be read.</strong>
          <p>{String(registry.error)}</p>
          <Button className="action-button" onClick={() => registry.refetch()}>
            Retry
          </Button>
        </div>
      </DataPanel>
    )
  const points = registry.data?.charge_points ?? []
  return (
    <DataPanel title="OCPP charge points" className="full">
      {points.length === 0 ? (
        <UnavailableState
          title="No charge point is connected"
          reason="Point a charger at ws://127.0.0.1:8000/ocpp/{charge_point_id} using OCPP 1.6 JSON."
        />
      ) : (
        <div className="table-scroll">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Charge point</TableHead>
                <TableHead>Identity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Transaction</TableHead>
                <TableHead>Power</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {points.map((point) => (
                <TableRow key={point.charge_point_id}>
                  <TableHead scope="row">{point.charge_point_id}</TableHead>
                  <TableCell>
                    {[point.vendor, point.model].filter(Boolean).join(' ') || 'Unknown'}
                  </TableCell>
                  <TableCell>{point.connected ? point.status : 'Disconnected'}</TableCell>
                  <TableCell>{point.transaction_id ?? '—'}</TableCell>
                  <TableCell>{formatPower(point.power_kw)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </DataPanel>
  )
}
