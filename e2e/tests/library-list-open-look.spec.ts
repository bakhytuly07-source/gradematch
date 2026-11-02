import { test, expect } from '@playwright/test';
import { generate, sample, styledPreview } from '../helpers';
import { register, uniqueName, save, thumbnail, openLook, adjust } from '../library-helpers';

test('empty Library, newest-first cards and independent saved controls survive reload', async ({ page }) => {
  await register(page);
  await page.getByRole('link', { name: 'Make your first look', exact: true }).click();
  await expect(page).toHaveURL('http://localhost:8091/');
  await generate(page);
  const older = uniqueName('Older'), newer = uniqueName('Newer');
  const oldValues = [73, 4, -3, 8], newValues = [86, -5, 6, -4];
  await adjust(page, oldValues);
  const first = await save(page, older);
  // Distinguishable creation times follow from finishing a real render before
  // the second save; verify the server timestamps rather than sleeping.
  await adjust(page, newValues);
  const second = await save(page, newer);
  expect(second.created_at).toBeGreaterThan(first.created_at);
  await page.getByRole('button', { name: 'Open library', exact: true }).last().click();
  await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
  for (const name of [older, newer]) {
    const article = await thumbnail(page, name);
    await expect(article.getByRole('button', { name: 'Add to favorites', exact: true })).toBeVisible();
  }
  await expect(page.getByRole('article').first().getByRole('img')).toHaveAttribute('alt', newer);
  await expect(page.getByRole('article').nth(1).getByRole('img')).toHaveAttribute('alt', older);
  await openLook(page, older, oldValues);
  await sample(page);
  await styledPreview(page);
  await page.getByRole('link', { name: 'Library', exact: true }).click();
  await openLook(page, newer, newValues);
  await page.getByRole('link', { name: 'Library', exact: true }).click();
  await page.reload();
  await thumbnail(page, older);
  await thumbnail(page, newer);
});
