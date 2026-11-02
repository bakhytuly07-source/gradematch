import { test, expect } from '@playwright/test';
import { openStudio, generate, sample, styledPreview, preview, pixels, dragDivider } from '../helpers';
test('pointer dragging changes the visible split and stops on release', async ({ page }) => {
  await openStudio(page);
  await generate(page);
  await sample(page);
  const expected = await styledPreview(page);
  await page.getByRole('button', { name: 'Before / after', exact: true }).click();
  const divider = page.getByRole('slider', { name: 'Before and after divider', exact: true });
  await expect(divider).toHaveValue('50');
  for (const percent of [25, 75, 0, 100]) {
    const box = await dragDivider(page, percent);
    // After's clip begins at the line; 0 reveals full After, 100 full Before.
    // Verify those original/styled canvas buffers stay intact throughout.
    expect(await pixels(page)).toEqual(expected);
    const released = await divider.inputValue();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await expect(divider).toHaveValue(released);
    const value = Number(released);
    expect(value).toBeGreaterThanOrEqual(0);
    expect(value).toBeLessThanOrEqual(100);
    if (percent === 0 || percent === 100) {
      const clip = await preview(page).locator('canvas').nth(1).evaluate(c => c.style.clipPath);
      expect(clip).toBe(`inset(0px 0px 0px ${percent}%)`);
    }
  }
});
