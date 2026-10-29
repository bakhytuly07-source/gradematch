// Guest workflow against Compose with Playwright-managed Chromium.
const {launch, prepare, FRONTEND_URL} = require('./support.cjs');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const os = require('node:os');
const root = path.resolve(__dirname, '../..');
(async () => {
 const browser = await launch();
 try {
  const page = await browser.newPage({acceptDownloads:true});
  const errors=[]; page.on('pageerror', e => errors.push(e.message));
  let latestLut, latestSettings; const operations=[];
  page.on('request', r => {if(r.url().includes(':8091/api/')) operations.push(r.method()+' '+new URL(r.url()).pathname);});
  page.on('response', async r => {if(r.url().endsWith('/api/render-lut') && r.ok()) {latestLut=await r.json();latestSettings=r.request().postDataJSON();}});
  await prepare(page);
  const restored=page.waitForResponse(r=>r.url().endsWith('/api/auth/me'));
  await page.goto(FRONTEND_URL, {waitUntil:'domcontentloaded'});
  await restored;
  await page.getByRole('button',{name:'Generate Color Style',exact:true}).waitFor();
  const input = page.locator('input[type=file]').first();
  // Client validation and recovery, followed by actual backend rejection.
  for (const file of [{name:'empty.jpg',mimeType:'image/jpeg',buffer:Buffer.alloc(0)},
    {name:'bad.gif',mimeType:'image/gif',buffer:Buffer.from('bad')},
    {name:'large.jpg',mimeType:'image/jpeg',buffer:Buffer.alloc(15728641)}]) {
    await input.setInputFiles(file);
    await page.locator('p.text-destructive').first().waitFor();
  }
  await input.setInputFiles({name:'corrupt.jpg',mimeType:'image/jpeg',buffer:Buffer.from([255,216,255,0])});
  const bad=page.waitForResponse(r=>r.url().endsWith('/api/generate'));
  await page.getByRole('button',{name:'Generate Color Style',exact:true}).click();
  assert.equal((await bad).status(),422);
  const image=fs.readFileSync(path.join(root,'backend/evaluation/reference-neutral.jpg'));
  const padded=Buffer.concat([image,Buffer.alloc(15728640-image.length)]);
  await input.setInputFiles({name:'15MiB.jpg',mimeType:'image/jpeg',buffer:padded});
  const generated=page.waitForResponse(r=>r.url().endsWith('/api/generate') && r.ok());
  const start=Date.now(); await page.getByRole('button',{name:'Generate Color Style',exact:true}).click();
  await generated; const generateMs=Date.now()-start;
  const cubeButton=page.getByRole('button',{name:'Download LUT (.cube)',exact:true});
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent==='Download LUT (.cube)'&&!b.disabled));
  await page.getByAltText('Lake sample').click();
  await page.locator('canvas').first().waitFor();
  await page.getByRole('button',{name:'Side by side',exact:true}).click();
  assert.equal(await page.locator('figure canvas').count(),2);
  assert.equal(await page.getByRole('slider',{name:'Before and after divider',exact:true}).count(),0);
  await page.getByRole('button',{name:'Before / after',exact:true}).click();
  const divider=page.getByRole('slider',{name:'Before and after divider',exact:true});
  await divider.focus(); await divider.press('ArrowRight');
  assert.equal(await divider.inputValue(),'51');
  await page.locator('input[type=file]').nth(1).setInputFiles(path.join(root,'frontend/src/assets/sample-portrait.jpg'));
  const previewMs=[];
  for (const label of ['Look intensity','Contrast','Saturation','Warmth']) {
    const slider=page.getByRole('slider',{name:label,exact:true});
    await slider.focus(); const t=Date.now();
    const response=page.waitForResponse(r=>r.url().endsWith('/api/render-lut')&&r.ok());
    await slider.press('ArrowRight'); await response;
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent==='Download LUT (.cube)'&&!b.disabled));
    previewMs.push(Date.now()-t);
  }
  // Exercise rapid changes; last settings and visible LUT must win.
  await page.getByRole('slider',{name:'Warmth',exact:true}).press('ArrowRight');
  await page.getByRole('slider',{name:'Warmth',exact:true}).press('ArrowRight');
  await page.waitForTimeout(400);
  const downloadEvent=page.waitForEvent('download'); await cubeButton.click(); const download=await downloadEvent;
  const cube=fs.readFileSync(await download.path(),'utf8');
  assert.match(cube, /^LUT_3D_SIZE 33$/m);
  const samples=cube.trim().split('\n').slice(4).flatMap(row=>row.trim().split(/\s+/).map(Number));
  assert.equal(samples.length,107811);
  assert.deepEqual(new Float32Array(samples),new Float32Array(latestLut.data));
  const ts=require(path.join(root,'frontend/node_modules/typescript'));
  const source=ts.transpileModule(fs.readFileSync(path.join(root,'frontend/src/lib/apply-lut.ts'),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText.replaceAll('export ','');
  await page.addScriptTag({content:source});
  const target=fs.readFileSync(path.join(root,'frontend/src/assets/sample-portrait.jpg')).toString('base64');
  const imageExports={};
  for(const format of ['PNG','JPEG']) {
    const event=page.waitForEvent('download'); await page.getByRole('button',{name:`Download image (${format})`,exact:true}).click();
    const output=fs.readFileSync(await (await event).path()).toString('base64');
    const comparison=await page.evaluate(async ({target,output,lut,format})=>{
      lut.data=new Float32Array(lut.data);
      const img=await loadImage('data:image/jpeg;base64,'+target);
      const expected=renderToCanvas(img,lut,6000);
      const actual=renderToCanvas(await loadImage('data:image/'+format.toLowerCase()+';base64,'+output),null,6000);
      const a=expected.getContext('2d').getImageData(0,0,expected.width,expected.height).data;
      const b=actual.getContext('2d').getImageData(0,0,actual.width,actual.height).data;
      let sum=0; for(let i=0;i<a.length;i++) sum+=Math.abs(a[i]-b[i]);
      return {width:actual.width,height:actual.height,mean_absolute_channel_error:sum/a.length};
    },{target,output,lut:latestLut,format});
    assert.ok(comparison.mean_absolute_channel_error < (format==='PNG'?0.001:3)); imageExports[format]=comparison;
  }
  assert.ok(generateMs <= 5000, 'generation target exceeded');
  console.log('preview_ms', previewMs);
  assert.ok(previewMs.every(ms => ms <= 300), 'preview target exceeded');
  assert.ok(!operations.some(x=>x==='POST /api/looks'));
  assert.deepEqual(errors,[]);
  const result={host:os.cpus()[0].model,browser:await browser.version(),method:'Headless Chromium UI, real HTTP backend, 15MiB padded JPEG; preview includes control debounce, HTTP and enabled current export. Host-specific fixture timing, not general performance qualification.',generate_ms:generateMs,preview_ms:previewMs,settings:latestSettings,cube_samples:samples.length,float32_cube_matches:true,image_exports:imageExports,guest_created_no_library_records:true,page_errors:errors};
  fs.writeFileSync(path.join(root,'work/e2e/guest-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
