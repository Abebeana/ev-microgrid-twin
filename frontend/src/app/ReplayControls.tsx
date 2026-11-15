import type { MicrogridSite } from '@/shared/api/contracts/site'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Pause, Play, SkipBack, SkipForward } from 'lucide-react'

type ReplayControlsProps = {
  rawTime: string
  site?: MicrogridSite
  playing: boolean
  stepTime: (direction: number) => void
  setPlaying: (playing: boolean) => void
  setRawTime: (value: string) => void
}
export function ReplayControls({
  rawTime,
  site,
  playing,
  stepTime,
  setPlaying,
  setRawTime,
}: ReplayControlsProps) {
  return (
    <div className="replay-control">
      <div className="time-input-row">
        <Button
          type="button"
          className="time-step"
          aria-label="Previous 15 minutes"
          onClick={() => stepTime(-1)}
        >
          <SkipBack size={15} />
        </Button>
        <Input
          id="replay-time"
          aria-label="Recorded time"
          type="datetime-local"
          value={rawTime}
          min={site?.metadata.first_raw.slice(0, 16).replace(' ', 'T')}
          max={site?.metadata.last_raw.slice(0, 16).replace(' ', 'T')}
          onChange={(event) => {
            setPlaying(false)
            setRawTime(event.target.value)
          }}
        />
        <Button
          type="button"
          className="time-step"
          aria-label="Next 15 minutes"
          onClick={() => stepTime(1)}
        >
          <SkipForward size={15} />
        </Button>
        <Button
          type="button"
          className="time-step play-toggle"
          aria-label={playing ? 'Pause replay' : 'Play replay'}
          aria-pressed={playing}
          onClick={() => setPlaying(!playing)}
        >
          {playing ? <Pause size={15} /> : <Play size={15} />}
        </Button>
      </div>
    </div>
  )
}
