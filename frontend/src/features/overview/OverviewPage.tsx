import { EnergyFlowDiagram } from '@/features/overview/EnergyFlowDiagram'
import { SiteSummaryMetrics } from '@/features/telemetry/SiteSummaryMetrics'
import { TrendRangeControl } from '@/features/telemetry/TrendRangeControl'
import { TelemetryTrendChart } from '@/shared/charts/TelemetryTrendChart'
import { DataPanel } from '@/shared/components/DataPanel'
import { formatSiteTime } from '@/shared/format/time'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { ArrowRight } from 'lucide-react'

export function OverviewPage() {
  const { alarms, availability, navigate } = useReplay()
  return (
    <>
      <SiteSummaryMetrics />
      <div className="content-grid">
        <DataPanel title="Energy" className="wide">
          <EnergyFlowDiagram />
        </DataPanel>
        <DataPanel
          title="Alarms"
          action={
            <Button className="text-link" onClick={() => navigate('/alarms')}>
              All <ArrowRight size={14} />
            </Button>
          }
        >
          {alarms.length ? (
            alarms.slice(0, 4).map((alarm) => (
              <Button key={alarm.id} className="attention-row" onClick={() => navigate('/alarms')}>
                <span className="severity">{alarm.severity}</span>
                <span>
                  <strong>{alarm.asset_id}</strong>
                  <small>{alarm.message}</small>
                </span>
                <small>{formatSiteTime(alarm.site_time)}</small>
              </Button>
            ))
          ) : (
            <p className="quiet">No events in the last 24 hours.</p>
          )}
        </DataPanel>
        <DataPanel title="Trend" className="wide" action={<TrendRangeControl />}>
          <TelemetryTrendChart series={['solar_kw', 'observed_charging_kw']} height={260} />
        </DataPanel>
        <DataPanel title="Plan">
          <p className="quiet">{availability.forecast.reason}</p>
          <Button className="action-button" onClick={() => navigate('/forecasts')}>
            Physical forecast
          </Button>
          <Button className="secondary-button" onClick={() => navigate('/scenarios')}>
            Scenario
          </Button>
        </DataPanel>
      </div>
    </>
  )
}
