import { X } from 'lucide-react'
import type { RefObject } from 'react'
import { icons } from './icons'
import { screens } from './routes'

const groups = ['Operations', 'Investigate', 'Plan', 'Assurance'] as const

type SidebarProps = {
  navOpen: boolean
  closeRef: RefObject<HTMLButtonElement | null>
  closeNav: () => void
  currentPath: string
  navigate: (path: string) => void
}

export function Sidebar({ navOpen, closeRef, closeNav, currentPath, navigate }: SidebarProps) {
  return (
    <aside
      id="primary-navigation"
      className={`sidebar ${navOpen ? 'open' : ''}`}
      aria-label="Primary navigation"
    >
      <div className="brand">
        <div className="brand-symbol">
          <img className="brand-mark" src={icons.electricity} alt="" width={20} height={20} />
        </div>
        <div className="brand-copy">
          <strong>SOFIE</strong>
          <span>EV microgrid</span>
        </div>
        <button
          type="button"
          ref={closeRef}
          className="mobile-close"
          aria-label="Close navigation"
          onClick={closeNav}
        >
          <X size={20} />
        </button>
      </div>
      <nav>
        {groups.map((group) => (
          <div className="nav-group" key={group}>
            <div className="nav-label">{group}</div>
            <ul className="nav-list">
              {screens
                .filter((item) => item.group === group)
                .map((item) => (
                  <li key={item.path}>
                    <button
                      type="button"
                      className={`nav-item ${currentPath === item.path ? 'active' : ''}`}
                      aria-current={currentPath === item.path ? 'page' : undefined}
                      onClick={() => navigate(item.path)}
                    >
                      <img
                        className="nav-icon"
                        src={icons[item.icon]}
                        alt=""
                        width={22}
                        height={22}
                      />
                      <span>{item.title}</span>
                    </button>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <span className="foot-dot" />
        Historical replay
      </div>
    </aside>
  )
}
