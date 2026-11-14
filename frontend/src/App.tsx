import { useEffect, useState, type MouseEvent } from 'react'
import alarm from '../../design/assets/icons/alarm.svg'
import architecture from '../../design/assets/icons/architecture.svg'
import battery from '../../design/assets/icons/battery.svg'
import charging from '../../design/assets/icons/charging.svg'
import compare from '../../design/assets/icons/compare.svg'
import electricity from '../../design/assets/icons/electricity.svg'
import forecast from '../../design/assets/icons/forecast.svg'
import graph from '../../design/assets/icons/graph.svg'
import inspection from '../../design/assets/icons/inspection.svg'
import optimizer from '../../design/assets/icons/optimizer.svg'
import overview from '../../design/assets/icons/overview.svg'
import scenario from '../../design/assets/icons/scenario.svg'
import solar from '../../design/assets/icons/solar.svg'
import sun from '../../design/assets/icons/sun.svg'
import telemetry from '../../design/assets/icons/telemetry.svg'
import validation from '../../design/assets/icons/validation.svg'

const pages = [
  { path: '/', title: 'Command Center', group: 'Operations', icon: overview },
  { path: '/site', title: '3D Site Twin', group: 'Operations', icon: solar },
  { path: '/electrical', title: 'Electrical One-Line', group: 'Operations', icon: electricity },
  { path: '/chargers', title: 'Charger Fleet & Queue', group: 'Operations', icon: charging },
  { path: '/inspect', title: 'Charger Inspection', group: 'Operations', icon: inspection },
  { path: '/solar', title: 'Solar Production', group: 'Operations', icon: sun },
  { path: '/battery', title: 'Battery State', group: 'Operations', icon: battery },
  { path: '/grid', title: 'Grid & Transformer', group: 'Operations', icon: electricity },
  { path: '/alarms', title: 'Alarm Triage', group: 'Investigate', icon: alarm },
  { path: '/telemetry', title: 'Telemetry Pipeline', group: 'Investigate', icon: telemetry },
  { path: '/stream', title: 'Simulated MQTT Stream', group: 'Investigate', icon: forecast },
  { path: '/graph', title: 'Ontology & Graph', group: 'Investigate', icon: graph },
  { path: '/forecasts', title: 'Forecasts', group: 'Plan', icon: forecast },
  { path: '/dispatch', title: 'Dispatch Optimizer', group: 'Plan', icon: optimizer },
  { path: '/scenarios', title: 'Scenario Builder', group: 'Plan', icon: scenario },
  { path: '/compare', title: 'Scenario Comparison', group: 'Plan', icon: compare },
  { path: '/rl-lab', title: 'PowerWise RL Lab', group: 'Plan', icon: optimizer },
  { path: '/validation', title: 'KPI Validation', group: 'Assurance', icon: validation },
  { path: '/health', title: 'Architecture & Health', group: 'Assurance', icon: architecture },
] as const

const groups = ['Operations', 'Investigate', 'Plan', 'Assurance'] as const

export default function App() {
  const [path, setPath] = useState(window.location.pathname)
  const [navOpen, setNavOpen] = useState(false)
  const page = pages.find((item) => item.path === path) ?? pages[0]

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    if (!navOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setNavOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [navOpen])

  function navigate(event: MouseEvent<HTMLAnchorElement>, target: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    if (target !== path) {
      window.history.pushState({}, '', target)
      setPath(target)
    }
    setNavOpen(false)
    window.setTimeout(() => document.getElementById('shell-heading')?.focus(), 0)
  }

  return (
    <div className="shell">
      <aside className={`sidebar ${navOpen ? 'open' : ''}`} aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-symbol"><img src={electricity} alt="" width="20" height="20" /></span>
          <span className="brand-copy"><strong>SOFIE</strong><small>EV microgrid</small></span>
          <button className="close-nav" type="button" onClick={() => setNavOpen(false)}>Close</button>
        </div>
        <nav>
          {groups.map((group) => (
            <section className="nav-group" key={group} aria-label={group}>
              <h2>{group}</h2>
              <ul>
                {pages.filter((item) => item.group === group).map((item) => (
                  <li key={item.path}>
                    <a
                      href={item.path}
                      className={`nav-item ${page.path === item.path ? 'active' : ''}`}
                      aria-current={page.path === item.path ? 'page' : undefined}
                      onClick={(event) => navigate(event, item.path)}
                    >
                      <img src={item.icon} alt="" width="22" height="22" />
                      <span>{item.title}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </nav>
        <div className="sidebar-foot"><span className="status-dot" />Shell preview</div>
      </aside>

      {navOpen && <button className="nav-scrim" type="button" aria-label="Close navigation" onClick={() => setNavOpen(false)} />}

      <div className="main-column">
        <header className="topbar">
          <button className="open-nav" type="button" aria-expanded={navOpen} onClick={() => setNavOpen(true)}>Menu</button>
          <h1>{page.title}</h1>
          <span className="mode-badge"><span className="status-dot" />Shell preview</span>
        </header>
        <main>
          <section className="page-shell" aria-labelledby="shell-heading">
            <p className="eyebrow">{page.group}</p>
            <h2 id="shell-heading" tabIndex={-1}>{page.title}</h2>
            <p>This page is a shell. Its details will be added in a later commit.</p>
          </section>
        </main>
      </div>
    </div>
  )
}
