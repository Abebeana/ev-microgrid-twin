import { Suspense } from 'react'
import { Database, Menu } from 'lucide-react'
import { Button } from '@/shared/ui/button'
import { Badge } from '@/shared/ui/badge'
import { NavigationContext, ReplayContext } from '@/shared/state/replay-context'
import { ReplayControls } from './ReplayControls'
import { icons } from './icons'
import { Sidebar } from './Sidebar'
import { useWorkbench } from './use-workbench'
import './workbench.css'

export function Workbench() {
  const {
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
  } = useWorkbench()
  const screen = (
    <Suspense fallback={<div className="loading-state">Loading workspace…</div>}>
      <CurrentScreen />
    </Suspense>
  )

  const replayControl = !streamPath && !experimentPath && (
    <ReplayControls
      rawTime={rawTime}
      site={site.data}
      playing={playing}
      stepTime={stepTime}
      setPlaying={setPlaying}
      setRawTime={setRawTime}
    />
  )

  return (
    <div className="shell">
      <Sidebar
        navOpen={navOpen}
        closeRef={closeRef}
        closeNav={closeNav}
        currentPath={current.path}
        navigate={navigate}
      />
      {navOpen && <Button className="nav-scrim" onClick={closeNav} aria-label="Close navigation" />}
      <div className="main-column" inert={navOpen}>
        <header className="topbar">
          <Button
            ref={menuRef}
            className="mobile-menu"
            onClick={() => setNavOpen(true)}
            aria-label="Open navigation"
            aria-expanded={navOpen}
            aria-controls="primary-navigation"
          >
            <Menu size={20} />
          </Button>
          <h1>{current.title}</h1>
          <div className="topbar-tools">
            {replayControl}
            <Button
              className="tool-button"
              onClick={() => {
                const next = theme === 'dark' ? 'light' : 'dark'
                document.documentElement.dataset.theme = next
                setTheme(next)
              }}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            >
              <img
                className="theme-icon"
                src={theme === 'dark' ? icons.sun : icons.moon}
                alt=""
                width={18}
                height={18}
              />
              <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </Button>
            <Badge variant="outline" className="mode-badge rounded-none">
              <span />{' '}
              {streamPath
                ? 'Simulated stream'
                : experimentPath
                  ? 'Simulated RL test'
                  : 'Historical replay'}
            </Badge>
          </div>
        </header>
        <main ref={mainRef} tabIndex={-1}>
          {streamPath || experimentPath ? (
            <NavigationContext.Provider value={{ navigate, setRawTime }}>
              {screen}
            </NavigationContext.Provider>
          ) : dataError ? (
            <div className="load-error" role="alert">
              <strong>Data could not be loaded.</strong>
              <p>{String(dataError.error)}</p>
              <Button className="action-button" onClick={refresh}>
                Retry
              </Button>
            </div>
          ) : !loaded ? (
            <div className="loading-state">
              <Database size={24} />
              <span>Loading…</span>
            </div>
          ) : (
            <ReplayContext.Provider
              value={{
                site: site.data!,
                snapshot: replay.data!,
                trend: trend.data!,
                alarms: alarms.data!,
                quality: quality.data!,
                graph: graph.data!,
                availability: availability.data!,
                sessions: sessions.data!,
                rawTime,
                setRawTime,
                hours,
                setHours,
                selectedBox,
                selectBox,
                navigate,
                refresh,
                scenarioA,
                setScenarioA,
                scenarioB,
                setScenarioB,
              }}
            >
              <NavigationContext.Provider value={{ navigate, setRawTime }}>
                {screen}
              </NavigationContext.Provider>
            </ReplayContext.Provider>
          )}
        </main>
      </div>
    </div>
  )
}
