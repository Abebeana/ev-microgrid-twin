import { useEffect, useRef, useState } from 'react'
import { type ScenarioResult } from '@/shared/api/contracts/scenarios'
import { queryClient } from './query-client'
import { screens } from './routes'
import { useReplayQueries } from './use-replay-queries'

export function useWorkbench() {
  const [path, setPath] = useState(window.location.pathname)
  const [rawTimeOverride, setRawTimeOverride] = useState<string | null>(() =>
    new URLSearchParams(window.location.search).get('at'),
  )
  const [hours, setHours] = useState(24)
  const [selectedBox, setSelectedBox] = useState<string | null>(null)
  const [scenarioA, setScenarioA] = useState<ScenarioResult | null>(null)
  const [scenarioB, setScenarioB] = useState<ScenarioResult | null>(null)
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    localStorage.getItem('twin-theme') === 'light' ? 'light' : 'dark',
  )
  const [navOpen, setNavOpen] = useState(false)
  const [playing, setPlaying] = useState(false)
  const streamPath = path === '/stream'
  const experimentPath = path === '/rl-lab'
  const mainRef = useRef<HTMLElement>(null)
  const menuRef = useRef<HTMLButtonElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const { site, replay, trend, alarms, sessions, graph, quality, availability, rawTime } =
    useReplayQueries(path, rawTimeOverride, hours)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('twin-theme', theme)
  }, [theme])
  useEffect(() => {
    const handler = () => {
      setPath(window.location.pathname)
      setRawTimeOverride(new URLSearchParams(window.location.search).get('at'))
      setPlaying(false)
    }
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])
  useEffect(() => {
    const mobile = window.matchMedia('(max-width: 900px)')
    const onResize = () => {
      if (!mobile.matches) setNavOpen(false)
    }
    mobile.addEventListener('change', onResize)
    return () => mobile.removeEventListener('change', onResize)
  }, [])
  useEffect(() => {
    if (!navOpen) return
    const focusTimer = window.setTimeout(() => closeRef.current?.focus(), 220)
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setNavOpen(false)
        window.setTimeout(() => menuRef.current?.focus(), 0)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(focusTimer)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [navOpen])
  const closeNav = () => {
    setNavOpen(false)
    window.setTimeout(() => menuRef.current?.focus(), 0)
  }
  const setRawTime = (value: string) => {
    setRawTimeOverride(value)
    const url = new URL(window.location.href)
    if (value) url.searchParams.set('at', value)
    else url.searchParams.delete('at')
    window.history.replaceState({}, '', url)
  }
  const stepTime = (direction: number) => {
    if (!rawTime || !site.data) return
    const next = new Date(`${rawTime.slice(0, 16)}:00Z`).getTime() + direction * 15 * 60_000
    const minimum = new Date(
      `${site.data.metadata.first_raw.slice(0, 16).replace(' ', 'T')}:00Z`,
    ).getTime()
    const maximum = new Date(
      `${site.data.metadata.last_raw.slice(0, 16).replace(' ', 'T')}:00Z`,
    ).getTime()
    if (next < minimum || next > maximum) {
      setPlaying(false)
      return
    }
    setRawTime(new Date(next).toISOString().slice(0, 16))
  }
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => stepTime(1), 1800)
    return () => window.clearInterval(timer)
  })
  const navigate = (target: string) => {
    if (target !== path) {
      window.history.pushState({}, '', target + window.location.search)
      if (target === '/stream') setPlaying(false)
      setPath(target)
      window.scrollTo(0, 0)
    }
    setNavOpen(false)
    window.setTimeout(() => mainRef.current?.focus(), 0)
  }
  const selectBox = (id: string) => {
    setSelectedBox(id)
    navigate('/inspect')
  }
  const refresh = () => {
    queryClient.invalidateQueries()
  }
  const current = screens.find((item) => item.path === path) ?? screens[0]
  const CurrentScreen = current.component
  const dataError = [site, replay, trend, alarms, sessions, graph, quality, availability].find(
    (query) => query.isError,
  )
  const loaded =
    site.data &&
    replay.data &&
    trend.data &&
    alarms.data &&
    sessions.data &&
    graph.data &&
    quality.data &&
    availability.data
  return {
    path,
    hours,
    setHours,
    selectedBox,
    scenarioA,
    setScenarioA,
    scenarioB,
    setScenarioB,
    theme,
    setTheme,
    navOpen,
    setNavOpen,
    playing,
    setPlaying,
    streamPath,
    experimentPath,
    mainRef,
    menuRef,
    closeRef,
    closeNav,
    setRawTime,
    stepTime,
    navigate,
    selectBox,
    refresh,
    current,
    CurrentScreen,
    dataError,
    loaded,
    site,
    replay,
    trend,
    alarms,
    sessions,
    graph,
    quality,
    availability,
    rawTime,
  }
}
