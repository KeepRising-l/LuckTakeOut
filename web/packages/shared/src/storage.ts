const PREFIX = 'takeout'

export const storage = {
  get(key: string): string | null {
    return localStorage.getItem(`${PREFIX}:${key}`)
  },
  set(key: string, value: string) {
    localStorage.setItem(`${PREFIX}:${key}`, value)
  },
  getJSON<T>(key: string): T | null {
    const raw = localStorage.getItem(`${PREFIX}:${key}`)
    if (!raw) return null
    try {
      return JSON.parse(raw) as T
    } catch {
      return null
    }
  },
  setJSON(key: string, value: unknown) {
    localStorage.setItem(`${PREFIX}:${key}`, JSON.stringify(value))
  },
  remove(key: string) {
    localStorage.removeItem(`${PREFIX}:${key}`)
  },
}
