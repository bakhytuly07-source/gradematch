// Regression #56. Requires the real API + frontend from integration/README.md.
const {launch, prepare, FRONTEND_URL} = require('./support.cjs');
const assert = require('node:assert/strict');
(async () => {
  const browser = await launch();
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    const nonce = require('node:crypto').randomUUID();
    await prepare(page);
    const restored = page.waitForResponse(r => r.url().endsWith('/api/auth/me'));
    await page.goto(FRONTEND_URL + '/register', {waitUntil:'domcontentloaded'});
    await restored;
    await page.getByLabel('Email',{exact:true}).fill(`studio-a-${nonce}@example.com`);
    await page.getByLabel('Password',{exact:true}).fill('password123');
    await page.getByRole('button',{name:'Create account',exact:true}).click();
    await page.getByText('No saved looks yet.',{exact:true}).waitFor();
    await page.evaluate(async () => {
      const service = new window.ApiService(window.e2eApiUrl);
      await service.saveLook({name:'A private style',thumbnail:'',styleParams:{id:'a-private',shadowTint:[0.1,0.2,0.3],highlightTint:[0.7,0.8,0.9],baseSaturation:1.2},adjustments:{intensity:91,contrast:21,saturation:31,warmth:41}});
    });
    // Navigate without reloading so the module-global Studio cache is exercised.
    await page.getByRole('link',{name:'Studio',exact:true}).click();
    await page.getByRole('button',{name:'Generate Color Style',exact:true}).waitFor();
    await page.getByRole('link',{name:'Library',exact:true}).click();
    await page.getByRole('link',{name:'Open',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('[role=slider][aria-label=Warmth]')?.getAttribute('aria-valuenow') === '41');
    await page.getByRole('link',{name:'Library',exact:true}).click();
    await page.getByRole('button',{name:'Log out',exact:true}).click();
    await page.getByRole('link',{name:'Log in',exact:true}).click();
    await page.getByRole('link',{name:'Create an account',exact:true}).click();
    await page.getByLabel('Email',{exact:true}).fill(`studio-b-${nonce}@example.com`);
    await page.getByLabel('Password',{exact:true}).fill('password123');
    await page.getByRole('button',{name:'Create account',exact:true}).click();
    await page.getByText('No saved looks yet.',{exact:true}).waitFor();
    await page.getByRole('link',{name:'Studio',exact:true}).click();
    for (const [label,value] of [['Look intensity','80'],['Contrast','0'],['Saturation','0'],['Warmth','0']])
      assert.equal(await page.getByRole('slider',{name:label,exact:true}).getAttribute('aria-valuenow'), value);
    assert.equal(await page.getByText('Preview',{exact:true}).count(),0);
    assert.equal(await page.getByRole('button',{name:'Download LUT (.cube)',exact:true}).isDisabled(),true);
    assert.deepEqual(errors,[]);
    console.log('PASS: real migrated API / Chromium account switch discards private Studio settings');
  } finally { await browser.close(); }
})().catch(e => {console.error(e);process.exitCode=1;});
