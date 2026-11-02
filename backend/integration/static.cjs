// Focused #95 check; existing guest/Library/Studio scenarios stay intact.
const {spawnSync} = require('node:child_process');
const assert = require('node:assert/strict');
const path = require('node:path');
const {launch, prepare, FRONTEND_URL} = require('./support.cjs');
const {ready} = require('./run.cjs');
(async () => {
  await ready();
  const browser = await launch();
  try {
    const page = await browser.newPage();
    await prepare(page);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const nonce = require('node:crypto').randomUUID();
    const email = `static-${nonce}@example.com`;
    const name = `Persistent ${nonce}`;
    for (const route of ['/login', '/library']) {
      const response = await page.goto(FRONTEND_URL + route);
      assert.equal(response.status(), 200);
      assert.equal((await page.reload()).status(), 200);
      await page.getByRole('heading', {name:'Welcome back', exact:true}).waitFor();
    }
    await page.goto(FRONTEND_URL + '/register');
    await page.getByLabel('Email', {exact:true}).fill(email);
    await page.getByLabel('Password', {exact:true}).fill('password123');
    await page.getByRole('button', {name:'Create account', exact:true}).click();
    await page.getByText('No saved looks yet.', {exact:true}).waitFor();
    await page.getByRole('link', {name:'Studio', exact:true}).click();
    await page.locator('input[type=file]').first().setInputFiles(path.resolve('backend/evaluation/reference-neutral.jpg'));
    await page.getByRole('button', {name:'Generate Color Style', exact:true}).click();
    await page.getByRole('button', {name:'☆ Save to Library', exact:true}).click();
    await page.getByPlaceholder('e.g. Golden hour').fill(name);
    const saved = page.waitForResponse(r => r.url().endsWith('/api/looks') && r.request().method() === 'POST');
    await page.getByRole('button', {name:'Save', exact:true}).click();
    assert.equal((await saved).status(), 201);
    const restart = spawnSync('docker', ['compose', 'restart', 'app'], {encoding:'utf8', timeout:60000});
    assert.equal(restart.status, 0, restart.stderr);
    await ready();
    await page.getByRole('button', {name:'Log out', exact:true}).click();
    await page.goto(FRONTEND_URL + '/login');
    await page.getByLabel('Email', {exact:true}).fill(email);
    await page.getByLabel('Password', {exact:true}).fill('password123');
    await page.getByRole('button', {name:'Log in', exact:true}).click();
    await page.getByRole('button', {name, exact:true}).waitFor();
    await page.reload();
    await page.getByRole('button', {name, exact:true}).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS #95: direct/reloaded routes, browser registration/save, app restart, fresh login and persisted look');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
