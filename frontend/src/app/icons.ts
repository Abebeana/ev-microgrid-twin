import alarm from '../../../design/assets/icons/alarm.svg'
import architecture from '../../../design/assets/icons/architecture.svg'
import battery from '../../../design/assets/icons/battery.svg'
import charging from '../../../design/assets/icons/charging.svg'
import compare from '../../../design/assets/icons/compare.svg'
import electricity from '../../../design/assets/icons/electricity.svg'
import forecast from '../../../design/assets/icons/forecast.svg'
import graph from '../../../design/assets/icons/graph.svg'
import inspection from '../../../design/assets/icons/inspection.svg'
import moon from '../../../design/assets/icons/moon.svg'
import optimizer from '../../../design/assets/icons/optimizer.svg'
import overview from '../../../design/assets/icons/overview.svg'
import scenario from '../../../design/assets/icons/scenario.svg'
import solar from '../../../design/assets/icons/solar.svg'
import sun from '../../../design/assets/icons/sun.svg'
import telemetry from '../../../design/assets/icons/telemetry.svg'
import validation from '../../../design/assets/icons/validation.svg'

export const icons = {
  alarm,
  architecture,
  battery,
  charging,
  compare,
  electricity,
  forecast,
  graph,
  inspection,
  moon,
  optimizer,
  overview,
  scenario,
  solar,
  sun,
  telemetry,
  validation,
} as const

export type IconName = keyof typeof icons
