import { postJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'
import { UnavailableState } from '@/shared/components/UnavailableState'
import { formatSiteTime } from '@/shared/format/time'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { Label } from '@/shared/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { Textarea } from '@/shared/ui/textarea'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { useState } from 'react'

export function AlarmTriagePage() {
  const { alarms, rawTime, refresh, selectBox, site } = useReplay()
  const [selected, setSelected] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const alarm = alarms.find((item) => item.id === selected)
  const ack = useMutation({
    mutationFn: () =>
      postJson('/api/alarms/acknowledge', {
        alarm_id: selected,
        note,
        at: `raw:${rawTime.replace(' ', 'T')}`,
      }),
    onSuccess: () => {
      setSelected(null)
      setNote('')
      refresh()
    },
  })
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'Recorded events',
            value: String(alarms.length),
            caption: 'Fault/error events and battery thresholds · 24 h',
          },
          {
            label: 'Unacknowledged',
            value: String(alarms.filter((item) => !item.acknowledgement).length),
            caption: 'At selected replay time',
          },
          {
            label: 'Source',
            value: 'SOFIE',
            caption: 'OCPP connector status and logging',
          },
          {
            label: 'Review mode',
            value: 'Local',
            caption: 'Notes are saved to the audit trail',
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Alarm triage" className="wide">
          <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Site time</TableHead>
                  <TableHead>Asset</TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alarms.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{formatSiteTime(item.site_time)}</TableCell>
                    <TableHead scope="row">{item.asset_id}</TableHead>
                    <TableCell>{item.message}</TableCell>
                    <TableCell>
                      {item.acknowledgement
                        ? `Acknowledged by ${item.acknowledgement.actor}`
                        : 'Open in review'}
                    </TableCell>
                    <TableCell>
                      <Button className="text-link" onClick={() => setSelected(item.id)}>
                        Inspect <ArrowRight size={13} />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {!alarms.length && (
            <p className="quiet">
              No fault or configured threshold events in the 24 hours before the selected replay
              time. This is not a live safety status.
            </p>
          )}
        </DataPanel>
        <DataPanel title="Event inspection">
          {alarm ? (
            <>
              <DetailList
                rows={[
                  { label: 'Event', value: alarm.message },
                  { label: 'Asset', value: alarm.asset_id },
                  {
                    label: 'Recorded at',
                    value: formatSiteTime(alarm.site_time),
                  },
                  { label: 'Source table', value: alarm.provenance },
                  {
                    label: 'Acknowledged',
                    value: alarm.acknowledgement?.note ?? 'No',
                  },
                ]}
              />
              {site.wallboxes.some((box) => box.id === alarm.asset_id) && (
                <Button className="action-button" onClick={() => selectBox(alarm.asset_id)}>
                  Inspect wallbox
                </Button>
              )}
              {!alarm.acknowledgement && (
                <form
                  className="ack-form"
                  onSubmit={(event) => {
                    event.preventDefault()
                    ack.mutate()
                  }}
                >
                  <Label htmlFor="ack-note">Operator note</Label>
                  <Textarea
                    id="ack-note"
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    required
                    maxLength={500}
                    placeholder="Record why this historical event was reviewed"
                  />
                  <Button type="submit" className="action-button" disabled={ack.isPending}>
                    Acknowledge in audit trail
                  </Button>
                  {ack.isError && (
                    <p className="error-text" role="alert">
                      {String(ack.error)}
                    </p>
                  )}
                </form>
              )}
            </>
          ) : (
            <UnavailableState
              title="Select an event"
              reason="Choose a recorded alarm to inspect its source and acknowledgement."
            />
          )}
        </DataPanel>
      </div>
    </>
  )
}
