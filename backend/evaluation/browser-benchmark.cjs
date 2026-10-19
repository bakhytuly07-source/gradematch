// Uses existing environment Playwright and existing frontend TypeScript compiler.
// No project dependencies are added. Run: node evaluation/browser-benchmark.cjs
const fs = require('node:fs');
const path = require('node:path');
const ts = require('../../frontend/node_modules/typescript');
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    const source = fs.readFileSync(path.join(__dirname, '../../frontend/src/lib/apply-lut.ts'), 'utf8');
    const js = ts.transpileModule(source, {compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022}}).outputText.replaceAll('export ', '');
    await page.addScriptTag({ content: js });
    const lut = JSON.parse(fs.readFileSync(path.join(__dirname, 'browser-lut.json')));
    const image = fs.readFileSync(path.join(__dirname, '../../frontend/src/assets/sample-lake.jpg')).toString('base64');
    const measurements = await page.evaluate(async ({lut, image}) => {
      const img = await loadImage('data:image/jpeg;base64,' + image);
      const timings = {};
      for (const [name, width, height] of [['preview', 1024, 768], ['full', 4000, 3000]]) {
        const canvas = document.createElement('canvas');
        canvas.width = width; canvas.height = height;
        const ctx = canvas.getContext('2d', {willReadFrequently: true});
        const runs = [];
        for (let i=0;i<6;i++) {
          ctx.drawImage(img, 0, 0, width, height);
          const start = performance.now();
          const pixels = ctx.getImageData(0, 0, width, height);
          applyLutToPixels(pixels.data, lut);
          ctx.putImageData(pixels, 0, 0);
          await new Promise(requestAnimationFrame);
          runs.push(performance.now() - start);
        }
        timings[name] = {width, height, cold_ms: runs[0], warm_ms: runs.slice(1)};
      }
      return {userAgent: navigator.userAgent, hardwareConcurrency: navigator.hardwareConcurrency, timings};
    }, {lut, image});
    const result = {lut_sha256: require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(__dirname, 'browser-lut.json'))).digest('hex'), browser: await browser.version(), ...measurements};
    fs.writeFileSync(path.join(__dirname, 'browser-results.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result, null, 2));
  } finally { await browser.close(); }
})();
