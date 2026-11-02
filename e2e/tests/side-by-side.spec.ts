import { test, expect } from '@playwright/test';
import { openStudio, generate, sample, styledPreview, section, fullImages, pixels, sourcePixels, expectedStyled, observeLut, dragDivider } from '../helpers';
test('comparison modes preserve complete target images and all four controls', async ({ page }) => {
  await openStudio(page);
  const currentLut = observeLut(page);
  await generate(page);
  await sample(page);
  const fineTune = section(page, 'Fine-tune');
  for (const name of ['Look intensity', 'Contrast', 'Saturation', 'Warmth']) {
    const rendered = page.waitForResponse(r => r.url().endsWith('/api/render-lut') && r.ok());
    await fineTune.getByRole('slider', { name, exact: true }).press('ArrowRight');
    await rendered;
    await expect(page.getByRole('button', { name: 'Download LUT (.cube)', exact: true })).toBeEnabled();
  }
  const displayedValues = await fineTune.innerText();
  const sliderValues = await fineTune.getByRole('slider').evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-valuenow')));
  expect(sliderValues).toEqual(['81', '1', '1', '1']);
  const expected = await styledPreview(page);
  const src = await page.getByRole('img', { name: 'Lake sample', exact: true }).getAttribute('src');
  expect(expected[0]).toEqual(await sourcePixels(page, src!));
  expect(expected[1]).toEqual(await expectedStyled(page, src!, await currentLut()));
  for (let turn = 0; turn < 2; turn++) {
    await page.getByRole('button', { name: 'Side by side', exact: true }).click();
    await fullImages(page, expected);
    await expect(page.getByRole('slider', { name: 'Before and after divider', exact: true })).toHaveCount(0);
    expect(await fineTune.innerText()).toBe(displayedValues);
    expect(await fineTune.getByRole('slider').evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-valuenow')))).toEqual(sliderValues);
    await page.getByRole('button', { name: 'Before / after', exact: true }).click();
    await expect(page.getByRole('slider', { name: 'Before and after divider', exact: true })).toBeAttached();
    await dragDivider(page, turn === 0 ? 25 : 75);
    expect(await pixels(page)).toEqual(expected);
    expect(await fineTune.innerText()).toBe(displayedValues);
    expect(await fineTune.getByRole('slider').evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-valuenow')))).toEqual(sliderValues);
  }
});
