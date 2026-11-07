import { useEffect, useState } from 'react'

type ApiStatus = 'checking' | 'connected' | 'offline'

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()

    fetch('/api/health', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API unavailable')
        return response.json() as Promise<{ status: string }>
      })
      .then((data) => setApiStatus(data.status === 'ok' ? 'connected' : 'offline'))
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setApiStatus('offline')
        }
      })

    return () => controller.abort()
  }, [])

  return (
    <main className="page">
      <div className="shell">
        <p className="eyebrow">Project scaffold</p>
        <h1>EV Microgrid Twin</h1>
        <p className="intro">A starting point for site data, analysis, and the twin interface.</p>

        <section className="status" aria-labelledby="status-title">
          <div>
            <h2 id="status-title">API connection</h2>
            <p>The backend health check at <code>/api/health</code>.</p>
          </div>
          <span className={`badge badge--${apiStatus}`} role="status">
            {apiStatus === 'checking' ? 'Checking' : apiStatus === 'connected' ? 'Connected' : 'Offline'}
          </span>
        </section>

        <p className="note">No telemetry is connected yet.</p>
      </div>
    </main>
  )
}
