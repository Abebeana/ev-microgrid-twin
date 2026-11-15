import { type Wallbox } from '@/shared/api/contracts/charging'

export type SiteView = 'overview' | 'solar' | 'battery' | string

export const CHARGER_X_POSITIONS = [-12, -4, 4, 12]

export const SITE_ACCENT_COLOR = '#8faf86'

export function stateOf(box: Wallbox) {
  if (box.error_code && box.error_code !== 'NoError') return 'fault'
  if (box.power_kw == null) return 'unavailable'
  return box.power_kw > 0.25 ? 'charging' : 'idle'
}

export function stateText(box: Wallbox) {
  return {
    fault: 'Fault',
    unavailable: 'No data',
    charging: 'Charging',
    idle: 'Idle',
  }[stateOf(box)]
}

export function positionFor(view: SiteView, boxes: Wallbox[]): [number, number, number] {
  const i = boxes.findIndex((box) => box.id === view)
  if (i >= 0) return [CHARGER_X_POSITIONS[i % 4], 1.3, i < 4 ? -3 : 3]
  if (view === 'battery') return [19, 1.5, 0]
  if (view === 'solar') return [0, 5, -7]
  return [2, 0, 0]
}
