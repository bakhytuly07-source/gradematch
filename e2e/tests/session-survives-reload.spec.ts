import { randomUUID } from 'node:crypto';
import { test, expect, type Page } from '@playwright/test';
import { generate, registerAccount } from '../helpers';

test('restores the saved look after reload and in a new tab of the same context', async ({ page, context }) => {
  const id = randomUUID();
  const name = `Session look ${id}`;
  await registerAccount(page, `session-${id}@example.com`, 'Session-password-123');
  await page.getByRole('banner').getByRole('link', { name: 'Studio', exact: true }).click();
  await generate(page);
  await page.getByRole('button', { name: 'Save to Library' }).click();
  const dialog = page.getByRole('dialog', { name: 'Name this look', exact: true });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('textbox').fill(name);
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole('banner').getByRole('link', { name: 'Library', exact: true }).click();

  async function expectSavedLook(tab: Page) {
    await expect(tab).toHaveURL('http://localhost:8091/library');
    await expect(tab.getByText('Restoring session…', { exact: true })).toHaveCount(0);
    await expect(tab.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
    await expect(tab.getByRole('banner').getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
    const look = tab.getByRole('article').filter({ has: tab.getByRole('button', { name, exact: true }) });
    await expect(look).toHaveCount(1);
    await expect(look).toBeVisible();
    await expect(tab.getByRole('heading', { name: 'Welcome back', exact: true })).toHaveCount(0);
  }
  await expectSavedLook(page);
  await page.reload();
  await expectSavedLook(page);
  const tab = await context.newPage();
  await tab.goto('/library');
  await expectSavedLook(tab);
});
