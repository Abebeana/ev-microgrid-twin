import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

import { useReplay } from '@/shared/state/replay-context'

export function MeasurementQualityTable() {
  const { quality } = useReplay()
  return (
    <div className="table-scroll">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Check</TableHead>
            <TableHead>Count</TableHead>
            <TableHead>Interpretation</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {quality.checks.map((check) => (
            <TableRow key={check.code}>
              <TableHead scope="row">{check.code.replaceAll('_', ' ')}</TableHead>
              <TableCell>{check.count.toLocaleString()}</TableCell>
              <TableCell>{check.detail}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
