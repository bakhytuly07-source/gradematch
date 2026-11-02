import { test, expect } from '@playwright/test';
import { openStudio, generate, sample, styledPreview, sourcePixels, expectedStyled, observeLut, pixels, fullImages, dragDivider } from '../helpers';
test('all bundled samples render their own original and styled pixels', async ({ page }) => {
  await openStudio(page);
  const currentLut = observeLut(page);
  await generate(page);
  let previous: any;
  for (const name of ['Lake', 'Portrait', 'Café']) {
    await sample(page, name);
    const src = await page.getByRole('img', { name: `${name} sample`, exact: true }).getAttribute('src');
    const original = await sourcePixels(page, src!);
    await expect.poll(async () => (await pixels(page))[0]).toEqual(original);
    const [before, after] = await styledPreview(page);
    expect(after).toEqual(await expectedStyled(page, src!, await currentLut()));
    if (previous) expect(before).not.toEqual(previous);
    previous = before;
  }
  const expected = await pixels(page);
  await page.getByRole('button', { name: 'Side by side', exact: true }).click();
  await fullImages(page, expected);
  await page.getByRole('button', { name: 'Before / after', exact: true }).click();
  await expect(page.getByRole('slider', { name: 'Before and after divider', exact: true })).toHaveValue('50');
  await dragDivider(page, 25);
  expect(await pixels(page)).toEqual(expected);
});
