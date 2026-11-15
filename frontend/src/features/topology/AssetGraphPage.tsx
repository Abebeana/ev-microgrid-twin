import { type GraphNode } from '@/shared/api/contracts/topology'
import { DataPanel } from '@/shared/components/DataPanel'
import { MetricStrip } from '@/shared/components/MetricStrip'
import { formatPercent, formatPower } from '@/shared/format/measurements'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { Background, Controls, Position, ReactFlow, type Edge, type Node } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

const entityTypes = [
  ['Site', 'SOFIE hub, kept as a Neo4j :Site node'],
  ['Solar', 'PV asset; site kW only when one unit exists'],
  ['Battery', 'Storage asset and measured SoC'],
  ['Bus', 'Islanded AC connection, no utility edge'],
  ['Charger', 'Discovered wallbox and observed power'],
  ['Telemetry sample', 'One recorded minute, retained in Neo4j'],
  ['Alert', 'Rule linked to the asset it concerns'],
]

const columns: Record<GraphNode['kind'], number> = {
  site: 0,
  solar: 1,
  battery: 1,
  other: 1,
  bus: 2,
  charger: 3,
  telemetry_sample: 4,
  alert: 5,
}

const relationStyle: Record<string, { color: string; dash?: string }> = {
  CONNECTED_TO: { color: 'var(--accent)' },
  HAS_ASSET: { color: 'var(--text-muted)' },
  OBSERVED_IN: { color: 'var(--text-muted)', dash: '4 4' },
  HAS_SAMPLE: { color: 'var(--text-muted)', dash: '2 4' },
  RAISED: { color: 'var(--error)' },
  ABOUT: { color: 'var(--error)', dash: '5 3' },
}

function nodeValue(node: GraphNode): string {
  if (node.kind === 'solar' || node.kind === 'charger') return formatPower(node.value)
  if (node.kind === 'battery') return formatPercent(node.value)
  if (node.kind === 'bus') return 'No grid connection'
  if (node.kind === 'site') return 'Islanded hub'
  if (node.kind === 'telemetry_sample') return node.recorded_at ?? node.name
  if (node.kind === 'alert') return node.rule?.replaceAll('_', ' ') ?? 'Review'
  return 'Configured asset'
}

function shortId(id: string): string {
  return id.replace('asset:', '').replace('wallbox:', '').replace('site:', '').replace('alert:', '')
}

function PathText({ hops }: { hops: string[] }) {
  if (!hops.length) return <span>No electrical path</span>
  return (
    <span className="graph-path">
      {hops.map((hop, index) => (
        <span key={`${hop}-${index}`}>
          {index > 0 && <span aria-hidden="true">→</span>}
          <code>{shortId(hop)}</code>
        </span>
      ))}
    </span>
  )
}

export function AssetGraphPage() {
  const { graph, selectBox, site, navigate } = useReplay()
  const styles = getComputedStyle(document.documentElement)
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const analytics = graph.analytics
  const history = graph.history
  const openNode = (node: GraphNode) => {
    if (node.wallbox_id) selectBox(node.wallbox_id)
    else if (node.kind === 'solar') navigate('/solar')
    else if (node.kind === 'battery') navigate('/battery')
    else if (node.kind === 'bus') navigate('/electrical')
    else if (node.kind === 'alert') navigate('/alarms')
    else if (node.kind === 'telemetry_sample') navigate('/telemetry')
  }
  const stacked = new Map<number, number>()
  const nodes: Node[] = graph.nodes.map((node) => {
    const column = columns[node.kind] ?? 1
    const index = stacked.get(column) ?? 0
    stacked.set(column, index + 1)
    return {
      id: node.id,
      position: { x: column * 210, y: index * 88 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: {
        label: (
          <div className="graph-node">
            <strong>{node.name}</strong>
            <span>{nodeValue(node)}</span>
          </div>
        ),
      },
      style: {
        background: 'var(--panel)',
        color: 'var(--text)',
        border: `1px solid ${node.kind === 'alert' ? 'var(--error)' : 'var(--border)'}`,
        borderRadius: 4,
        minWidth: 150,
        boxShadow: 'none',
      },
    }
  })
  const drawnRelations = new Set(['CONNECTED_TO', 'RAISED', 'ABOUT'])
  const edges: Edge[] = graph.edges.flatMap((edge) => {
    const relation = edge.relation ?? 'CONNECTED_TO'
    if (!drawnRelations.has(relation)) return []
    const stroke = relationStyle[relation] ?? relationStyle.CONNECTED_TO
    return [
      {
        id: `${edge.source}-${relation}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        animated: relation === 'CONNECTED_TO' && !reduceMotion,
        style: {
          stroke: styles.getPropertyValue(stroke.color.slice(4, -1)).trim() || stroke.color,
          strokeWidth: relation === 'CONNECTED_TO' ? 1.75 : 1,
          strokeDasharray: stroke.dash,
        },
      },
    ]
  })
  const solarIds = new Set(
    graph.nodes.filter((node) => node.kind === 'solar').map((node) => node.id),
  )
  const solarPaths = analytics.electrical_paths.filter((path) => solarIds.has(path.source))
  const solarChargers = new Set(solarPaths.map((path) => path.target))
  const solarReached = new Set(
    solarPaths.filter((path) => path.hops.length > 0).map((path) => path.target),
  )
  const examplePath =
    solarPaths.find((path) => path.hops.length > 1) ??
    analytics.electrical_paths.find((path) => path.hops.length > 1)
  return (
    <>
      <MetricStrip
        items={[
          { label: 'Graph store', value: graph.store, caption: 'Bolt property graph' },
          {
            label: 'Entity nodes',
            value: String(graph.nodes.length),
            caption: `${analytics.census.labels.length} Neo4j labels in this minute`,
          },
          {
            label: 'Relationships',
            value: String(graph.edges.length),
            caption: 'Typed edges, including alert links',
          },
          {
            label: 'Utility nodes',
            value: String(analytics.utility_nodes),
            caption: analytics.islanded ? 'Islanded; no grid node' : 'A grid node is present',
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Ontology and asset graph" className="wide">
          <p className="graph-note">
            {graph.note} The drawing shows electrical links and alert links. Membership and
            measurement edges stay in Neo4j.
          </p>
          <div className="graph-legend">
            {Object.entries(relationStyle).map(([relation, stroke]) => (
              <span key={relation}>
                <i
                  style={{
                    borderTopColor: stroke.color,
                    borderTopStyle: stroke.dash ? 'dashed' : 'solid',
                  }}
                />
                {relation.replaceAll('_', ' ').toLowerCase()}
              </span>
            ))}
          </div>
          <div className="graph-canvas" aria-label="Neo4j island topology for the selected minute">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              minZoom={0.2}
              onNodeClick={(_, item) => {
                const selected = graph.nodes.find((node) => node.id === item.id)
                if (selected) openNode(selected)
              }}
            >
              <Background gap={20} color={styles.getPropertyValue('--border').trim()} />
              <Controls />
            </ReactFlow>
          </div>
          <details className="chart-data">
            <summary>Browse graph assets as a list</summary>
            <div className="graph-asset-list">
              {graph.nodes.map((node) =>
                node.kind === 'other' ? (
                  <div key={node.id}>
                    {node.name}
                    <span>{nodeValue(node)}</span>
                  </div>
                ) : (
                  <Button key={node.id} onClick={() => openNode(node)}>
                    {node.name}
                    <span>{nodeValue(node)}</span>
                  </Button>
                ),
              )}
            </div>
          </details>
        </DataPanel>
        <DataPanel title="Bus traversal">
          <p className="graph-note">
            {solarReached.size} of {solarChargers.size || site.wallboxes.length} chargers are
            reached from solar across the islanded bus.
          </p>
          {examplePath && (
            <p className="graph-note">
              Shortest path <PathText hops={examplePath.hops} />
            </p>
          )}
          <div className="table-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Charger</TableHead>
                  <TableHead>Path from bus</TableHead>
                  <TableHead>Power</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analytics.downstream.map((row) => (
                  <TableRow key={row.charger_id}>
                    <TableHead scope="row">{row.name}</TableHead>
                    <TableCell>
                      <PathText hops={row.path} />
                    </TableCell>
                    <TableCell>{formatPower(row.power_kw)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Button className="action-button" onClick={() => navigate('/stream')}>
            Inspect current stream graph
          </Button>
        </DataPanel>
        <DataPanel title="Alert exposure" className="full">
          {analytics.alerts.length ? (
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rule</TableHead>
                    <TableHead>About</TableHead>
                    <TableHead>Same island</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analytics.alerts.map((alert) => (
                    <TableRow key={alert.id}>
                      <TableHead scope="row">{alert.message}</TableHead>
                      <TableCell>{alert.about.map(shortId).join(', ')}</TableCell>
                      <TableCell>{alert.exposed.map(shortId).join(', ') || 'None'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="quiet">No rule is linked to an asset at this minute.</p>
          )}
        </DataPanel>
        <DataPanel title="Minutes retained in Neo4j" className="wide">
          <div className="graph-summary">
            <div>
              <strong>{history.samples}</strong>
              <span>recorded minutes</span>
            </div>
            <div>
              <strong>{history.alerts}</strong>
              <span>retained alerts</span>
            </div>
          </div>
          {history.recent.length ? (
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Recorded minute</TableHead>
                    <TableHead>Alerts</TableHead>
                    <TableHead>Rules</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.recent.map((sample) => (
                    <TableRow key={sample.recorded_at}>
                      <TableHead scope="row">{sample.recorded_at}</TableHead>
                      <TableCell>{sample.alert_count}</TableCell>
                      <TableCell>{sample.rules.join(', ') || 'None'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="quiet">Open a replay minute or accept a stream frame to retain it.</p>
          )}
        </DataPanel>
        <DataPanel title="Repeated exposure">
          {history.repeated_exposure.length ? (
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rule</TableHead>
                    <TableHead>Asset</TableHead>
                    <TableHead>Minutes</TableHead>
                    <TableHead>Exposed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.repeated_exposure.map((row) => (
                    <TableRow key={`${row.rule}-${row.asset_id}`}>
                      <TableCell>{row.rule.replaceAll('_', ' ')}</TableCell>
                      <TableCell>{row.asset_name ?? shortId(row.asset_id)}</TableCell>
                      <TableCell>{row.minutes}</TableCell>
                      <TableCell>{row.exposed.map(shortId).join(', ') || 'None'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="quiet">No retained alert is tied to a catalog asset yet.</p>
          )}
        </DataPanel>
        <DataPanel title="Labels and queries" className="full">
          <div className="ontology-types">
            {entityTypes.map(([name, meaning]) => (
              <div key={name}>
                <strong>{name}</strong>
                <span>{meaning}</span>
              </div>
            ))}
          </div>
          {analytics.queries.length > 0 && (
            <details className="chart-data">
              <summary>Cypher used for this minute</summary>
              {analytics.queries.map((query) => (
                <div key={query.name} className="graph-query">
                  <strong>{query.name}</strong>
                  <pre>{query.cypher}</pre>
                </div>
              ))}
            </details>
          )}
        </DataPanel>
      </div>
    </>
  )
}
