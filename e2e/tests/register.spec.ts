import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { openRegistration, registerAccount } from '../helpers';

const email = () => `register-${randomUUID()}@example.com`;
const password = 'Register-password-123';

test('registers from Log in and recovers from a duplicate email', async ({ page }) => {
  const address = email();
  await registerAccount(page, address, password);
  await expect(page.getByText('No saved looks yet.', { exact: true })).toBeVisible();
  await page.getByRole('banner').getByRole('button', { name: 'Log out', exact: true }).click();
  await openRegistration(page);
  await page.getByLabel('Email', { exact: true }).fill(address);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByText('An account with this email already exists.', { exact: true })).toBeVisible();
  await expect(page.getByRole('banner').getByRole('link', { name: 'Log in', exact: true })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill(email());
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
  await expect(page.getByText('No saved looks yet.', { exact: true })).toBeVisible();
  await expect(page.getByRole('banner').getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
});

test('validates malformed email and a seven-character password', async ({ page }) => {
  await openRegistration(page);
  await page.getByLabel('Email', { exact: true }).fill('invalid-email');
  await page.getByLabel('Password', { exact: true }).fill('1234567');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByText("That email doesn't look right.", { exact: true })).toBeVisible();
  await expect(page.getByText('Password needs at least 8 characters.', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Create your account', exact: true })).toBeVisible();
});

test('validates empty registration fields', async ({ page }) => {
  await openRegistration(page);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByText('Enter your email.', { exact: true })).toBeVisible();
  await expect(page.getByText('Enter a password.', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Create your account', exact: true })).toBeVisible();
});
