import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

import { type Session } from '@/shared/api/contracts/charging'
import { formatSiteTime } from '@/shared/format/time'

export function ChargingSessionTable({ rows }: { rows: Session[] }) {
  if (!rows.length) return <p className="quiet">No sessions.</p>
  return (
    <div className="table-scroll">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Wallbox</TableHead>
            <TableHead>Started</TableHead>
            <TableHead>Stopped</TableHead>
            <TableHead>Meter delta</TableHead>
            <TableHead>Stop reason</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.transaction_id}>
              <TableHead scope="row">{row.wallbox_id}</TableHead>
              <TableCell>{formatSiteTime(row.start_site_time)}</TableCell>
              <TableCell>{formatSiteTime(row.stop_site_time)}</TableCell>
              <TableCell>
                {row.meter_delta_raw == null ? '—' : row.meter_delta_raw.toLocaleString()}
              </TableCell>
              <TableCell>{row.stop_reason ?? 'Open'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
