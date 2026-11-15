export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new Error(await detail(response))
  return response.json() as Promise<T>
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(await detail(response))
  return response.json() as Promise<T>
}

async function detail(response: Response): Promise<string> {
  try {
    const json = await response.json()
    return typeof json.detail === 'string' ? json.detail : `Request failed (${response.status})`
  } catch {
    return `Request failed (${response.status})`
  }
}
