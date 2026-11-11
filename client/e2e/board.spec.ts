import { expect, test } from '@playwright/test'

test('log in, create a task and move it across the board', async ({ page, request }) => {
  const email = `e2e-${Date.now()}@example.com`
  const password = 'password123'
  const reg = await request.post('/api/auth/register', { data: { email, password } })
  expect(reg.status()).toBe(201)

  await page.goto('/')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()

  await page.getByLabel('New project name').fill('E2E project')
  await page.getByRole('button', { name: 'Create project' }).click()
  await page.getByRole('button', { name: /E2E project/ }).click()

  await page.getByLabel('New task title').fill('Ship it')
  await page.getByRole('button', { name: 'Add task' }).click()
  const todo = page.getByRole('region', { name: 'To do' })
  const doing = page.getByRole('region', { name: 'Doing' })
  await expect(todo.getByText('Ship it')).toBeVisible()

  await page.getByRole('button', { name: 'Move "Ship it" to Doing' }).click()
  await expect(doing.getByText('Ship it')).toBeVisible()
  await expect(todo.getByText('Ship it')).toHaveCount(0)

  // survives a reload, so the move really hit the API
  await page.reload()
  await page.getByRole('button', { name: /E2E project/ }).click()
  await expect(page.getByRole('region', { name: 'Doing' }).getByText('Ship it')).toBeVisible()
})
