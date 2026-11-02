import { test, expect } from '@playwright/test';
import { openStudio, generate } from '../helpers';
import { register, uniqueName, save, thumbnail, openLook, adjust } from '../library-helpers';

test('guest save prompts login without opening a naming dialog', async ({ page }) => {
  await openStudio(page);
  await generate(page);
  await page.getByRole('button', { name: '☆ Save to Library', exact: true }).click();
  await expect(page.getByText('Log in to save looks to your library.', { exact: true })).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back', exact: true })).toBeVisible();
});

test('named and untitled saves persist with their saved warmth', async ({ page }) => {
  await register(page);
  await page.getByRole('link', { name: 'Make your first look', exact: true }).click();
  await generate(page);
  await adjust(page, [80, 0, 0, 30]);
  const name = uniqueName('Warm saved look');
  await save(page, name);
  await page.getByRole('button', { name: 'Open library', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
  await thumbnail(page, name);
  await page.reload();
  await thumbnail(page, name);
  await openLook(page, name, [80, 0, 0, 30]);
  await generate(page);
  await save(page, '');
  await page.getByRole('button', { name: 'Open library', exact: true }).click();
  await thumbnail(page, 'Untitled look');
  await page.reload();
  await thumbnail(page, 'Untitled look');
  await thumbnail(page, name);
});
