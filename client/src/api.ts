export type Status = 'todo' | 'doing' | 'done'
export type Priority = 'low' | 'medium' | 'high'

export type Project = { id: number; name: string; description: string; role: string }
export type Task = {
  id: number
  title: string
  status: Status
  priority: Priority
  due_date: string | null
}

let token = localStorage.getItem('token')

export const isLoggedIn = () => token !== null

export function logout() {
  token = null
  localStorage.removeItem('token')
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (typeof init.body === 'string') headers.set('Content-Type', 'application/json')
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (res.status === 401 && token) logout()
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const msg = body?.error?.message
    throw new Error(typeof msg === 'string' ? msg : `Request failed (${res.status})`)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export async function login(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password })
  const res = await request<{ access_token: string }>('/auth/login', { method: 'POST', body: form })
  token = res.access_token
  localStorage.setItem('token', token)
}

export const listProjects = () => request<Project[]>('/projects')

export const createProject = (name: string) =>
  request<Project>('/projects', { method: 'POST', body: JSON.stringify({ name }) })

// ponytail: one page of 100 tasks per board; add paging when a board outgrows it
export const listTasks = (projectId: number) =>
  request<{ items: Task[] }>(`/projects/${projectId}/tasks?limit=100&sort=-priority`).then(
    (r) => r.items,
  )

export const createTask = (projectId: number, title: string) =>
  request<Task>(`/projects/${projectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  })

export const updateTask = (projectId: number, taskId: number, patch: Partial<Task>) =>
  request<Task>(`/projects/${projectId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
