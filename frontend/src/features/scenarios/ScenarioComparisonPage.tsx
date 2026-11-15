import { Button } from '@/shared/ui/button'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

import { useMutation, useQuery } from '@tanstack/react-query'

import { getJson } from '@/shared/api/http-client'

import { type ScenarioInput, type ScenarioResult } from '@/shared/api/contracts/scenarios'
import { formatSiteTime } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { DataPanel } from '@/shared/components/DataPanel'
import { UnavailableState } from '@/shared/components/UnavailableState'

type SavedRun = {
  run_hash: string
  actor: string
  created_at: string
  request: ScenarioInput
  totals: ScenarioResult['totals']
}

function sameWindow(a: ScenarioResult, b: ScenarioResult): boolean {
  return (
    a.provenance.source_sha256 === b.provenance.source_sha256 &&
    a.schedule.length === b.schedule.length &&
    a.schedule.every((row, index) => row.raw_time === b.schedule[index].raw_time)
  )
}

export function ScenarioComparisonPage() {
  const { scenarioA, scenarioB, setScenarioA, setScenarioB, navigate } = useReplay()
  const saved = useQuery({
    queryKey: ['saved-scenarios'],
    queryFn: () => getJson<SavedRun[]>('/api/scenarios/saved'),
  })
  const restore = useMutation({
    mutationFn: ({ hash }: { hash: string; slot: 'A' | 'B' }) =>
      getJson<{ result: ScenarioResult }>(`/api/scenarios/saved/${hash}`),
    onSuccess: (data, variables) => {
      if (variables.slot === 'A') setScenarioA(data.result)
      else setScenarioB(data.result)
    },
  })
  const comparable = scenarioA && scenarioB && sameWindow(scenarioA, scenarioB)
  return (
    <div className="content-grid">
      <DataPanel title="Scenario comparison" className="wide">
        {comparable ? (
          <>
            <div className="compare-grid">
              <div>
                <span className="panel-eyebrow">Scenario A</span>
                <strong>{scenarioA.totals.unserved_ev_kwh.toFixed(2)} kWh</strong>
                <small>Modeled unserved EV energy</small>
                <code>{scenarioA.run_hash.slice(0, 16)}</code>
              </div>
              <div>
                <span className="panel-eyebrow">Scenario B</span>
                <strong>{scenarioB.totals.unserved_ev_kwh.toFixed(2)} kWh</strong>
                <small>Modeled unserved EV energy</small>
                <code>{scenarioB.run_hash.slice(0, 16)}</code>
              </div>
            </div>
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Outcome</TableHead>
                    <TableHead>Scenario A</TableHead>
                    <TableHead>Scenario B</TableHead>
                    <TableHead>B − A</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(['unserved_ev_kwh', 'curtailed_pv_kwh', 'battery_discharge_kwh'] as const).map(
                    (key) => (
                      <TableRow key={key}>
                        <TableHead scope="row">{key.replaceAll('_', ' ')}</TableHead>
                        <TableCell>{scenarioA.totals[key].toFixed(2)} kWh</TableCell>
                        <TableCell>{scenarioB.totals[key].toFixed(2)} kWh</TableCell>
                        <TableCell>
                          {(scenarioB.totals[key] - scenarioA.totals[key]).toFixed(2)} kWh
                        </TableCell>
                      </TableRow>
                    ),
                  )}
                </TableBody>
              </Table>
            </div>
          </>
        ) : scenarioA && scenarioB ? (
          <UnavailableState
            title="Runs use different recorded windows"
            reason="Choose A and B with the same start time and horizon before comparing modeled outcomes."
            action={
              <Button className="action-button" onClick={() => navigate('/scenarios')}>
                Open scenario builder
              </Button>
            }
          />
        ) : (
          <UnavailableState
            title="Two runs needed"
            reason="Evaluate two what-ifs or restore saved runs into A and B. The recorded window must match."
            action={
              <Button className="action-button" onClick={() => navigate('/scenarios')}>
                Open scenario builder
              </Button>
            }
          />
        )}
      </DataPanel>
      <DataPanel title="Saved runs">
        {saved.isError ? (
          <div role="alert">
            <p className="error-text">{String(saved.error)}</p>
            <Button className="secondary-button" onClick={() => saved.refetch()}>
              Retry
            </Button>
          </div>
        ) : saved.isPending ? (
          <p className="quiet">Loading saved runs…</p>
        ) : saved.data?.length ? (
          <div className="saved-list">
            {saved.data.map((run) => (
              <div key={run.run_hash}>
                <strong>{run.run_hash.slice(0, 16)}</strong>
                <span>
                  {run.actor} · {formatSiteTime(run.created_at)}
                </span>
                <small>
                  {run.request.start.replace('raw:', '')} · {run.request.hours} h · EV ×
                  {run.request.charging_multiplier} · PV ×{run.request.solar_multiplier}
                </small>
                <small>Unserved EV: {run.totals.unserved_ev_kwh.toFixed(2)} kWh</small>
                <div className="saved-actions">
                  <Button
                    className="secondary-button"
                    disabled={restore.isPending}
                    onClick={() => restore.mutate({ hash: run.run_hash, slot: 'A' })}
                  >
                    Use as A
                  </Button>
                  <Button
                    className="secondary-button"
                    disabled={restore.isPending}
                    onClick={() => restore.mutate({ hash: run.run_hash, slot: 'B' })}
                  >
                    Use as B
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="quiet">
            No saved runs yet. Save a completed what-if to keep its inputs and result.
          </p>
        )}
        {restore.isError && (
          <p role="alert" className="error-text">
            Could not restore run: {String(restore.error)}
          </p>
        )}
      </DataPanel>
    </div>
  )
}
