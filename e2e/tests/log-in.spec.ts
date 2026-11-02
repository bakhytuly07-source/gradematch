import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { openStudio, registerAccount } from '../helpers';

test('rejects a wrong password, then logs in with corrected credentials', async ({ page }) => {
  const email = `login-${randomUUID()}@example.com`;
  const password = 'Login-password-123';
  await registerAccount(page, email, password);
  const header = page.getByRole('banner');
  await header.getByRole('button', { name: 'Log out', exact: true }).click();
  await header.getByRole('link', { name: 'Log in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back', exact: true })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill('Wrong-password-123');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  const error = page.getByText('Email or password is incorrect.', { exact: true });
  await expect(error).toBeVisible();
  await expect(header.getByRole('button', { name: 'Log out', exact: true })).toHaveCount(0);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
  await expect(header.getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
  await expect(error).toHaveCount(0);
});

test('validates empty login fields', async ({ page }) => {
  await openStudio(page);
  await page.getByRole('banner').getByRole('link', { name: 'Log in', exact: true }).click();
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByText('Enter your email.', { exact: true })).toBeVisible();
  await expect(page.getByText('Enter your password.', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Welcome back', exact: true })).toBeVisible();
});
