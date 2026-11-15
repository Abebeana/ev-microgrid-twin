import { formatPercent, formatPower } from '@/shared/format/measurements'
import { useReplay } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { ArrowRight, BatteryCharging, Sun, Zap } from 'lucide-react'

export function EnergyFlowDiagram() {
  const { snapshot, navigate } = useReplay()
  return (
    <div className="energy-flow" aria-label="Measured energy sources and observed EV load">
      <div className="flow-column">
        <Button onClick={() => navigate('/solar')} className="flow-node">
          <Sun size={19} />
          <span>
            PV<strong>{formatPower(snapshot.solar_kw)}</strong>
          </span>
        </Button>
        <Button onClick={() => navigate('/battery')} className="flow-node">
          <BatteryCharging size={19} />
          <span>
            Battery<strong>{formatPercent(snapshot.battery_soc_pct)}</strong>
          </span>
        </Button>
      </div>
      <div className="flow-line" aria-hidden="true" />
      <div className="flow-node bus-node">
        <Zap size={21} />
        <span>
          Bus<strong>Unmeasured</strong>
        </span>
      </div>
      <div className="flow-line" aria-hidden="true" />
      <Button onClick={() => navigate('/chargers')} className="flow-node">
        <span>
          EV load<strong>{formatPower(snapshot.observed_charging_kw)}</strong>
          <small>
            {snapshot.observed_wallboxes}/{snapshot.total_wallboxes}
          </small>
        </span>
        <ArrowRight size={18} />
      </Button>
    </div>
  )
}
