import { test, expect } from '@playwright/test';
import { generate } from '../helpers';
import { register, uniqueName, save, card, thumbnail } from '../library-helpers';

test('favorite and unfavorite persist, with favorites first', async ({ page }) => {
  await register(page);
  await page.getByRole('link', { name: 'Make your first look', exact: true }).click();
  await generate(page);
  const older = uniqueName('Older'), newer = uniqueName('Newer');
  await save(page, older);
  await save(page, newer);
  await page.getByRole('banner').getByRole('link', { name: 'Library', exact: true }).click();
  await thumbnail(page, older);
  await thumbnail(page, newer);
  await expect(page.getByRole('article').first().getByRole('img')).toHaveAttribute('alt', newer);
  const empty = () => card(page, older).getByRole('button', { name: 'Add to favorites', exact: true });
  const filled = () => card(page, older).getByRole('button', { name: 'Remove from favorites', exact: true });
  await expect(empty()).toHaveText('☆');
  await empty().click();
  for (const reload of [false, true]) {
    if (reload) await page.reload();
    await expect(filled()).toHaveText('★');
    await expect(page.getByRole('article').first().getByRole('img')).toHaveAttribute('alt', older);
    await thumbnail(page, newer);
  }
  await filled().click();
  await expect(empty()).toHaveText('☆');
  await page.reload();
  await expect(empty()).toHaveText('☆');
  await thumbnail(page, older);
  await thumbnail(page, newer);
  await expect(page.getByRole('article')).toHaveCount(2);
});
