import { test, expect } from '@playwright/test';
import { generate } from '../helpers';
import { register, uniqueName, save, card, thumbnail } from '../library-helpers';

test('cancel preserves looks, confirmed deletion persists through the empty state', async ({ page }) => {
  await register(page);
  await page.getByRole('link', { name: 'Make your first look', exact: true }).click();
  await generate(page);
  const first = uniqueName('Delete'), second = uniqueName('Keep');
  await save(page, first);
  await save(page, second);
  await page.getByRole('banner').getByRole('link', { name: 'Library', exact: true }).click();
  async function remove(name: string, accept: boolean) {
    const handled = new Promise<void>((resolve, reject) => page.once('dialog', async dialog => {
      try {
        expect(dialog.type()).toBe('confirm');
        expect(dialog.message()).toBe(`Delete "${name}"?`);
        if (accept) await dialog.accept(); else await dialog.dismiss();
        resolve();
      } catch (error) { reject(error); }
    }));
    await card(page, name).getByRole('button', { name: 'Delete', exact: true }).click();
    await handled;
  }
  await remove(first, false);
  await thumbnail(page, first);
  await thumbnail(page, second);
  await page.reload();
  await thumbnail(page, first);
  await thumbnail(page, second);
  await remove(first, true);
  await expect(card(page, first)).toHaveCount(0);
  await thumbnail(page, second);
  await page.reload();
  await thumbnail(page, second);
  await expect(card(page, first)).toHaveCount(0);
  await remove(second, true);
  for (const reload of [false, true]) {
    if (reload) await page.reload();
    await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
    await expect(page.getByText('No saved looks yet.', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Make your first look', exact: true })).toBeVisible();
    await expect(page.getByRole('article')).toHaveCount(0);
  }
});
