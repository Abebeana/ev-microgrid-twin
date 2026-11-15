import { Button } from '@/shared/ui/button'

import { useReplay } from '@/shared/state/replay-context'

export function TrendRangeControl() {
  const { hours, setHours } = useReplay()
  return (
    <div className="segmented" role="group" aria-label="Trend range">
      {[6, 24, 72].map((hour) => (
        <Button
          key={hour}
          type="button"
          aria-pressed={hours === hour}
          onClick={() => setHours(hour)}
        >
          {hour} h
        </Button>
      ))}
    </div>
  )
}
