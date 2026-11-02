import { test, expect } from '@playwright/test';
import { openStudio, uploadReference, section, success } from '../helpers';
test('reference generation exposes progress and a usable real LUT', async ({ page }, testInfo) => {
  await openStudio(page);
  await uploadReference(page);
  const ref = section(page, 'Photo you love');
  await expect(ref.locator('img')).toBeVisible();
  const button = page.getByRole('button', { name: 'Generate Color Style', exact: true });
  await expect(button).toBeEnabled();
  // Passive observation catches short-lived progress without delaying the real API.
  await ref.evaluate(element => {
    const observations: { text: string; disabled: boolean; progressVisible: boolean }[] = [];
    (window as any).generationObservations = observations;
    new MutationObserver(() => {
      const b = Array.from(element.querySelectorAll('button')).find(b => b.textContent?.startsWith('Reading colors'));
      if (b) observations.push({ text: b.textContent!, disabled: b.disabled,
        progressVisible: Array.from(element.querySelectorAll('div')).some(d => d.style.width.endsWith('%') && d.getBoundingClientRect().width > 0 && d.getBoundingClientRect().height > 0) });
    }).observe(element, { subtree: true, childList: true, attributes: true, characterData: true });
  });
  const generated = page.waitForResponse(r => r.url().endsWith('/api/generate'));
  const start = Date.now();
  await button.click();
  expect((await generated).status()).toBe(200);
  await expect(page.getByText(success, { exact: true })).toBeVisible();
  const duration = Date.now() - start;
  console.log(`generation duration ${duration} ms; product target 5000 ms`);
  testInfo.annotations.push({ type: 'generation-duration', description: `${duration} ms against 5000 ms target` });
  expect(duration).toBeLessThanOrEqual(5000);
  const observations = await page.evaluate(() => (window as any).generationObservations);
  expect(observations.some((o: any) => /^Reading colors… \d+%$/.test(o.text) && o.disabled && o.progressVisible)).toBe(true);
  await expect(page.getByRole('button', { name: 'Generate again', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Download LUT (.cube)', exact: true })).toBeEnabled();
  await expect(page.getByText('Preview', { exact: true })).toBeVisible();
  for (const format of ['PNG', 'JPEG']) await expect(page.getByRole('button', { name: `Download image (${format})`, exact: true })).toBeDisabled();
});
