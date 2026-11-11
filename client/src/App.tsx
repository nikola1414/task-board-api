import { useEffect, useState, type FormEvent } from 'react'
import * as api from './api'
import type { Project, Status, Task } from './api'

const COLUMNS: { status: Status; label: string }[] = [
  { status: 'todo', label: 'To do' },
  { status: 'doing', label: 'Doing' },
  { status: 'done', label: 'Done' },
]

export default function App() {
  const [loggedIn, setLoggedIn] = useState(api.isLoggedIn())
  const [project, setProject] = useState<Project | null>(null)

  const logout = () => {
    api.logout()
    setProject(null)
    setLoggedIn(false)
  }

  return (
    <div className="app">
      <header>
        <h1>Task Board</h1>
        {loggedIn && (
          <nav>
            {project && <button onClick={() => setProject(null)}>All projects</button>}
            <button onClick={logout}>Log out</button>
          </nav>
        )}
      </header>
      <main>
        {!loggedIn ? (
          <Login onDone={() => setLoggedIn(true)} />
        ) : project ? (
          <Board project={project} />
        ) : (
          <ProjectList onOpen={setProject} />
        )}
      </main>
    </div>
  )
}

function Login({ onDone }: { onDone: () => void }) {
  const [error, setError] = useState('')

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    try {
      await api.login(String(form.get('email')), String(form.get('password')))
      onDone()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <form className="card login" onSubmit={submit}>
      <h2>Sign in</h2>
      <label>
        Email
        <input name="email" type="email" autoComplete="username" required />
      </label>
      <label>
        Password
        <input name="password" type="password" autoComplete="current-password" required />
      </label>
      {error && <p role="alert" className="error">{error}</p>}
      <button type="submit">Sign in</button>
    </form>
  )
}

function ProjectList({ onOpen }: { onOpen: (p: Project) => void }) {
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [name, setName] = useState('')

  useEffect(() => {
    api.listProjects().then(setProjects)
  }, [])

  async function create(e: FormEvent) {
    e.preventDefault()
    const p = await api.createProject(name)
    setProjects((prev) => [...(prev ?? []), p])
    setName('')
  }

  if (!projects) return <p>Loading…</p>
  return (
    <section>
      <h2>Your projects</h2>
      <ul className="projects">
        {projects.map((p) => (
          <li key={p.id}>
            <button className="card project" onClick={() => onOpen(p)}>
              <strong>{p.name}</strong>
              <span className="muted">{p.role}</span>
            </button>
          </li>
        ))}
      </ul>
      {projects.length === 0 && <p className="muted">No projects yet.</p>}
      <form className="inline" onSubmit={create}>
        <input
          aria-label="New project name"
          placeholder="New project name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit">Create project</button>
      </form>
    </section>
  )
}

function Board({ project }: { project: Project }) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [title, setTitle] = useState('')
  const [error, setError] = useState('')
  const canEdit = project.role !== 'viewer'

  useEffect(() => {
    api.listTasks(project.id).then(setTasks)
  }, [project.id])

  async function create(e: FormEvent) {
    e.preventDefault()
    try {
      const t = await api.createTask(project.id, title)
      setTasks((prev) => [...prev, t])
      setTitle('')
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function move(task: Task, status: Status) {
    try {
      const updated = await api.updateTask(project.id, task.id, { status })
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)))
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section>
      <h2>{project.name}</h2>
      {canEdit && (
        <form className="inline" onSubmit={create}>
          <input
            aria-label="New task title"
            placeholder="New task title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <button type="submit">Add task</button>
        </form>
      )}
      {error && <p role="alert" className="error">{error}</p>}
      <div className="board">
        {COLUMNS.map((col, i) => (
          <section key={col.status} className="column" aria-label={col.label}>
            <h3>
              {col.label}{' '}
              <span className="muted">{tasks.filter((t) => t.status === col.status).length}</span>
            </h3>
            {tasks
              .filter((t) => t.status === col.status)
              .map((t) => (
                <article key={t.id} className="card task">
                  <p>{t.title}</p>
                  <div className="meta">
                    <span className={`badge ${t.priority}`}>{t.priority}</span>
                    {t.due_date && <span className="muted">due {t.due_date}</span>}
                  </div>
                  {canEdit && (
                    <div className="actions">
                      {i > 0 && (
                        <button
                          aria-label={`Move "${t.title}" to ${COLUMNS[i - 1].label}`}
                          onClick={() => move(t, COLUMNS[i - 1].status)}
                        >
                          ←
                        </button>
                      )}
                      {i < COLUMNS.length - 1 && (
                        <button
                          aria-label={`Move "${t.title}" to ${COLUMNS[i + 1].label}`}
                          onClick={() => move(t, COLUMNS[i + 1].status)}
                        >
                          →
                        </button>
                      )}
                    </div>
                  )}
                </article>
              ))}
          </section>
        ))}
      </div>
    </section>
  )
}
