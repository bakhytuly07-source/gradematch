import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { registerAccount } from '../helpers';

test('logout protects Library after navigation, reload, and direct entry', async ({ page }) => {
  await registerAccount(page, `logout-${randomUUID()}@example.com`, 'Logout-password-123');
  const header = page.getByRole('banner');
  await header.getByRole('button', { name: 'Log out', exact: true }).click();
  await expect(page).toHaveURL('http://localhost:8091/');
  await expect(page.getByRole('button', { name: 'Generate Color Style', exact: true })).toBeVisible();
  await expect(header.getByRole('link', { name: 'Log in', exact: true })).toBeVisible();
  await expect(header.getByRole('button', { name: 'Log out', exact: true })).toHaveCount(0);
  await header.getByRole('link', { name: 'Library', exact: true }).click();
  async function expectLogin() {
    await expect(page.getByRole('heading', { name: 'Welcome back', exact: true })).toBeVisible();
    await expect(page.getByLabel('Email', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Password', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log in', exact: true })).toBeVisible();
    await expect(header.getByRole('link', { name: 'Log in', exact: true })).toBeVisible();
    await expect(header.getByRole('button', { name: 'Log out', exact: true })).toHaveCount(0);
    await expect(page.getByRole('article')).toHaveCount(0);
  }
  await expectLogin();
  await page.reload();
  await expectLogin();
  await page.goto('/library');
  await expectLogin();
});
