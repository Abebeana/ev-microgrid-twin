import { Button } from '@/shared/ui/button'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

import { ArrowRight } from 'lucide-react'

import { formatPower } from '@/shared/format/measurements'
import { formatSiteTime } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { SiteSummaryMetrics } from '@/features/telemetry/SiteSummaryMetrics'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'

import { ChargingSessionTable } from './ChargingSessionTable'
import { OcppSessionsPanel } from './OcppSessionsPanel'

export function ChargerFleetPage() {
  const { snapshot, sessions, selectBox } = useReplay()
  return (
    <>
      <SiteSummaryMetrics />
      <div className="content-grid">
        <DataPanel title="Charger fleet" className="wide">
          <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Wallbox</TableHead>
                  <TableHead>Last status</TableHead>
                  <TableHead>Measured power</TableHead>
                  <TableHead>Sample time</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshot.wallboxes.map((box) => (
                  <TableRow key={box.id}>
                    <TableHead scope="row">{box.id}</TableHead>
                    <TableCell>
                      <span className={`status ${box.status === 'Faulted' ? 'warn' : ''}`}>
                        {box.status}
                      </span>
                      {box.status_stale && <small className="subtle"> · old event</small>}
                    </TableCell>
                    <TableCell>{formatPower(box.power_kw)}</TableCell>
                    <TableCell>{formatSiteTime(box.power_site_time)}</TableCell>
                    <TableCell>
                      <Button className="text-link" onClick={() => selectBox(box.id)}>
                        Inspect <ArrowRight size={13} />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DataPanel>
        <DataPanel title="Fleet coverage">
          <DetailList
            rows={[
              {
                label: 'Configured wallboxes',
                value: snapshot.total_wallboxes,
              },
              {
                label: 'Power reporting',
                value: `${snapshot.observed_wallboxes}/${snapshot.total_wallboxes}`,
              },
              { label: 'Active transactions', value: snapshot.active_sessions },
              { label: 'Queue / reservations', value: 'Unavailable in SOFIE' },
            ]}
          />
        </DataPanel>
        <DataPanel title="Recent charging sessions" className="full">
          <ChargingSessionTable rows={sessions.slice(0, 10)} />
        </DataPanel>
        <OcppSessionsPanel />
      </div>
    </>
  )
}
