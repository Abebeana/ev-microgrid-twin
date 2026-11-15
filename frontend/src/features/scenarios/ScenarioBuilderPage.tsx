import { Label } from '@/shared/ui/label'

import { Button } from '@/shared/ui/button'

import { Input } from '@/shared/ui/input'

import { NativeSelect } from '@/shared/ui/native-select'

import { useState } from 'react'

import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ArrowRight, FlaskConical, Save } from 'lucide-react'

import { postJson } from '@/shared/api/http-client'

import { type ScenarioInput, type ScenarioResult } from '@/shared/api/contracts/scenarios'
import { rawAt } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'

export function ScenarioBuilderPage() {
  const { rawTime, site, selectedBox, scenarioA, setScenarioA, setScenarioB, navigate } =
    useReplay()
  const queryClient = useQueryClient()
  const [start, setStart] = useState(rawTime.replace(' ', 'T').slice(0, 16))
  const [hours, setHours] = useState(1)
  const [charging, setCharging] = useState(100)
  const [solar, setSolar] = useState(100)
  const [capacity, setCapacity] = useState(String(site.config.battery_capacity_kwh))
  const [outage, setOutage] = useState('')
  const [lastInput, setLastInput] = useState<ScenarioInput | null>(null)
  const [lastResult, setLastResult] = useState<ScenarioResult | null>(null)
  const [slot, setSlot] = useState<'A' | 'B'>('A')
  const build = (): ScenarioInput => ({
    start: rawAt(start),
    hours,
    charging_multiplier: charging / 100,
    solar_multiplier: solar / 100,
    battery_capacity_kwh: Number(capacity),
    outage_wallbox_id: outage || null,
  })
  const run = useMutation({
    mutationFn: ({ request }: { request: ScenarioInput; slot: 'A' | 'B' }) =>
      postJson<ScenarioResult>('/api/scenarios/evaluate', request),
    onSuccess: (result, variables) => {
      setLastInput(variables.request)
      setLastResult(result)
      if (variables.slot === 'A') setScenarioA(result)
      else setScenarioB(result)
    },
  })
  const save = useMutation({
    mutationFn: () => postJson('/api/scenarios/save', { scenario: lastInput }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['saved-scenarios'] }),
  })
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'Scenario',
            value: slot,
            caption: 'Independent what-if run',
          },
          {
            label: 'Horizon',
            value: `${hours} h`,
            caption: `${site.config.optimizer_step_minutes}-minute intervals`,
          },
          {
            label: 'Charging assumption',
            value: `${charging}%`,
            caption: 'User-supplied multiplier',
          },
          {
            label: 'Battery capacity',
            value: `${capacity} kWh`,
            caption: 'User-supplied assumption',
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Scenario inputs" className="wide">
          <form
            className="scenario-form"
            onSubmit={(event) => {
              event.preventDefault()
              run.mutate({ request: build(), slot })
            }}
          >
            <div className="form-row">
              <Label htmlFor="scenario-start">
                Recorded source time · {site.config.source_timestamp_timezone}
              </Label>
              <Input
                id="scenario-start"
                type="datetime-local"
                value={start}
                min={site.metadata.first_raw.slice(0, 16).replace(' ', 'T')}
                max={site.metadata.last_raw.slice(0, 16).replace(' ', 'T')}
                step={site.config.optimizer_step_minutes * 60}
                onChange={(event) => setStart(event.target.value)}
                required
              />
            </div>
            <div className="form-row">
              <Label htmlFor="scenario-hours">Horizon</Label>
              <NativeSelect
                id="scenario-hours"
                value={hours}
                onChange={(event) => setHours(Number(event.target.value))}
              >
                {[1, 2, 3, 4, 6, 12, 24].map((value) => (
                  <option key={value} value={value}>
                    {value} hour{value > 1 ? 's' : ''}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="form-row">
              <Label htmlFor="scenario-charging">
                Observed EV demand multiplier <strong>{charging}%</strong>
              </Label>
              <Input
                id="scenario-charging"
                type="range"
                min={0}
                max={200}
                step={5}
                value={charging}
                onChange={(event) => setCharging(Number(event.target.value))}
              />
            </div>
            <div className="form-row">
              <Label htmlFor="scenario-solar">
                Measured PV multiplier <strong>{solar}%</strong>
              </Label>
              <Input
                id="scenario-solar"
                type="range"
                min={0}
                max={200}
                step={5}
                value={solar}
                onChange={(event) => setSolar(Number(event.target.value))}
              />
            </div>
            <div className="form-row">
              <Label htmlFor="scenario-capacity">Battery capacity · kWh</Label>
              <Input
                id="scenario-capacity"
                type="number"
                min="0.1"
                max="200"
                step="0.1"
                value={capacity}
                onChange={(event) => setCapacity(event.target.value)}
                required
              />
            </div>
            <div className="form-row">
              <Label htmlFor="scenario-outage">Wallbox outage</Label>
              <NativeSelect
                id="scenario-outage"
                value={outage}
                onChange={(event) => setOutage(event.target.value)}
              >
                <option value="">None</option>
                {site.wallboxes.map((box) => (
                  <option key={box.id} value={box.id}>
                    {box.id}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="form-actions">
              <Button
                type="button"
                className="secondary-button"
                aria-pressed={slot === 'A'}
                onClick={() => setSlot('A')}
              >
                Run as A
              </Button>
              <Button
                type="button"
                className="secondary-button"
                aria-pressed={slot === 'B'}
                onClick={() => setSlot('B')}
              >
                Run as B
              </Button>
              <Button type="submit" className="action-button" disabled={run.isPending}>
                <FlaskConical size={15} />{' '}
                {run.isPending ? 'Solving…' : `Evaluate scenario ${slot}`}
              </Button>
            </div>
          </form>
          {run.isError && (
            <p role="alert" className="error-text">
              {String(run.error)}
            </p>
          )}
        </DataPanel>
        <DataPanel title="Experiment rules">
          <DetailList
            rows={[
              { label: 'Source', value: 'SOFIE measured history' },
              { label: 'PV and load', value: 'Observed subset only' },
              { label: 'Grid', value: 'Absent · islanded' },
              { label: 'Initial SoC', value: 'Measured at start' },
              {
                label: 'Battery efficiency',
                value: `${(site.config.battery_model_efficiency * 100).toFixed(0)}% assumption`,
              },
              { label: 'Selected inspection', value: selectedBox ?? 'None' },
              { label: 'Control', value: 'Advisory only' },
            ]}
          />
          {lastResult && (
            <div className="result-actions">
              <Button className="action-button" onClick={() => navigate('/compare')}>
                Compare runs <ArrowRight size={14} />
              </Button>
              <Button
                className="secondary-button"
                disabled={save.isPending}
                onClick={() => save.mutate()}
              >
                <Save size={14} /> Save with audit trail
              </Button>
              {save.isSuccess && <p className="success-text">Run saved.</p>}
              {save.isError && <p className="error-text">{String(save.error)}</p>}
            </div>
          )}
        </DataPanel>
        <DataPanel title="Reproducibility" className="full">
          {lastResult && (
            <div className="hash-line">
              Last run <code>{lastResult.run_hash}</code>
            </div>
          )}
          {scenarioA && (
            <div className="hash-line">
              Scenario A <code>{scenarioA.run_hash}</code>
            </div>
          )}
        </DataPanel>
      </div>
    </>
  )
}
