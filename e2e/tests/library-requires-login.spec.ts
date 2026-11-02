import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { generate, registerAccount } from '../helpers';
import { uniqueName, save, thumbnail } from '../library-helpers';

test('direct and header Library entry require login and preserve the return destination', async ({ page }) => {
  const email = `library-gate-${randomUUID()}@example.com`, password = 'Library-password-123';
  const name = uniqueName('Private');
  const header = page.getByRole('banner');
  await registerAccount(page, email, password);
  await header.getByRole('link', { name: 'Studio', exact: true }).click();
  await generate(page);
  await save(page, name);
  await header.getByRole('button', { name: 'Log out', exact: true }).click();
  await expect(page).toHaveURL('http://localhost:8091/');
  await page.goto('/library');
  async function gate() {
    await expect(page.getByRole('heading', { name: 'Welcome back', exact: true })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe('/login');
    expect(new URL(page.url()).searchParams.get('redirect')).toBe('/library');
    await expect(page.getByLabel('Email', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Password', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log in', exact: true })).toBeVisible();
    await expect(page.getByRole('article')).toHaveCount(0);
  }
  async function login(secret: string) {
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Password', { exact: true }).fill(secret);
    await page.getByRole('button', { name: 'Log in', exact: true }).click();
  }
  async function library() {
    await expect(page).toHaveURL('http://localhost:8091/library');
    await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
    await expect(header.getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
    await thumbnail(page, name);
  }
  await gate();
  await login(password);
  await library();
  await header.getByRole('button', { name: 'Log out', exact: true }).click();
  await expect(page).toHaveURL('http://localhost:8091/');
  await header.getByRole('link', { name: 'Library', exact: true }).click();
  await gate();
  await login('Incorrect-password-123');
  await expect(page.getByText('Email or password is incorrect.', { exact: true })).toBeVisible();
  await gate();
  await login(password);
  await library();
});
