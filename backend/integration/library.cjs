// Real UI + real adapter, against a migrated disposable backend. No new packages.
const {chromium}=require('playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage({acceptDownloads:true});const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error('BROWSER ERROR',e.stack,e.cause);});
  const nonce=Date.now(); const email=`integration-${nonce}@example.com`; const name=`Integration ${nonce}`;
  const restored=page.waitForResponse(r=>r.url().endsWith('/api/auth/me'));
  await page.goto('http://localhost:5173/register',{waitUntil:'domcontentloaded'}); await restored;
  await page.getByLabel('Email',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill('password123');
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByText('No saved looks yet.',{exact:true}).waitFor();
  await page.getByRole('link',{name:'Studio',exact:true}).click();
  await page.locator('input[type=file]').first().setInputFiles(path.join(root,'backend/evaluation/reference-neutral.jpg'));
  await page.getByRole('button',{name:'Generate Color Style',exact:true}).click();
  const ready=()=>page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent==='Download LUT (.cube)'&&!b.disabled));
  await ready();
  for(const label of ['Look intensity','Contrast','Saturation','Warmth']) await page.getByRole('slider',{name:label,exact:true}).press('ArrowRight');
  await ready();await page.getByAltText('Lake sample').click();
  await page.getByRole('button',{name:'☆ Save to Library',exact:true}).click();
  await page.getByPlaceholder('e.g. Golden hour').fill(name);
  const savedResponse=page.waitForResponse(r=>r.url().endsWith('/api/looks')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Save',exact:true}).click();
  const response=await savedResponse; assert.equal(response.status(),201);const saved=await response.json();
  const thumbnail=await page.evaluate(async src=>{const image=new Image();image.src=src;await image.decode();return [image.width,image.height];},saved.thumbnail_url);
  assert.equal(Math.max(...thumbnail),256);
  await page.getByRole('link',{name:'Library',exact:true}).click();
  await page.getByRole('button',{name,exact:true}).click();
  const editor=page.locator('main input');await editor.fill('   Renamed integration   ');
  const renamed=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().includes('/api/looks/'));
  await editor.press('Enter');assert.equal((await renamed).status(),200);
  await page.getByRole('button',{name:'Renamed integration',exact:true}).waitFor();
  // Blank rename stays recoverable; use Escape by clicking Rename again after error.
  await page.getByRole('button',{name:'Renamed integration',exact:true}).click();await editor.fill('  ');
  const blank=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().includes('/api/looks/'));
  await editor.press('Enter');assert.equal((await blank).status(),422);
  await editor.fill('Renamed integration');await editor.press('Enter');
  await page.getByRole('button',{name:'Renamed integration',exact:true}).waitFor();
  const favorite=page.waitForResponse(r=>r.url().endsWith('/favorite'));
  await page.getByRole('button',{name:'Add to favorites',exact:true}).click(); assert.equal((await favorite).status(),200);
  await page.reload({waitUntil:'domcontentloaded'});
  await page.getByRole('button',{name:'Remove from favorites',exact:true}).waitFor();
  await page.getByRole('link',{name:'Open',exact:true}).click();
  await ready();
  await page.locator('input[type=file]').nth(1).setInputFiles(path.join(root,'frontend/src/assets/sample-portrait.jpg'));
  const reopened=await page.evaluate(async id=>{const {ApiService}=await import('/src/services/api.ts');const api=new ApiService('http://localhost:8091');const look=await api.getLook(id);const lut=await api.renderLut(look.styleParams,look.adjustments);const cube=await (await api.downloadLutCube(look.styleParams,look.adjustments)).text();const values=new Float32Array(cube.trim().split('\n').slice(4).flatMap(row=>row.split(/\s+/).map(Number)));return {look,parity:values.every((v,i)=>v===lut.data[i])};},saved.id);
  assert.deepEqual(reopened.look.adjustments,saved.adjustments);assert.deepEqual(reopened.look.styleParams,saved.style_params);assert.equal(reopened.parity,true);
  // Exercise every foreign-id operation through real service instances, including
  // a missing-id comparison. Separate storage=null keeps the UI account intact.
  const isolation=await page.evaluate(async ({id,nonce})=>{
    const {ApiService}=await import('/src/services/api.ts');const a=new ApiService('http://localhost:8091');const b=new ApiService('http://localhost:8091',null);
    await b.register(`other-${nonce}@example.com`,'password123');const empty=(await b.listLooks()).length===0;
    const attempt=async run=>{try{await run();return 'unexpected success';}catch(e){return `${e.code}:${e.message}`;}};
    const foreign=await Promise.all([attempt(()=>b.getLook(id)),attempt(()=>b.renameLook(id,'foreign')),attempt(()=>b.toggleFavorite(id)),attempt(()=>b.deleteLook(id))]);
    const missing=await attempt(()=>b.getLook('missing'));
    const original=await a.getLook(id);
    const other=await a.saveLook({name:'Keep me',thumbnail:'',styleParams:original.styleParams,adjustments:original.adjustments});
    await b.logout();await b.login(`other-${nonce}@example.com`,'password123');await b.logout();
    return {empty,foreign,missing,secondId:other.id};
  },{id:saved.id,nonce});
  assert.equal(isolation.empty,true);assert.ok(isolation.foreign.every(x=>x===isolation.missing&&x.startsWith('not_found:')));
  await page.getByRole('link',{name:'Library',exact:true}).click();
  const article=page.locator('article').filter({has:page.getByRole('button',{name:'Renamed integration',exact:true})});
  page.once('dialog',d=>d.accept());const deleted=page.waitForResponse(r=>r.request().method()==='DELETE');
  await article.getByRole('button',{name:'Delete',exact:true}).click();assert.equal((await deleted).status(),204);
  await page.getByRole('button',{name:'Keep me',exact:true}).waitFor();
  await page.getByRole('button',{name:'Renamed integration',exact:true}).waitFor({state:'hidden'});
  await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'Keep me',exact:true}).waitFor();
  // Simulate a revoked token, then exercise the UI logout 401 cleanup.
  await page.evaluate(async()=>{const {ApiService}=await import('/src/services/api.ts');await new ApiService('http://localhost:8091').logout();});
  await page.getByRole('button',{name:'Log out',exact:true}).click();
  await page.getByRole('link',{name:'Log in',exact:true}).waitFor();
  await page.waitForFunction(()=>!Object.keys(sessionStorage).some(key=>key.startsWith('gradematch.token:')));
  await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('link',{name:'Log in',exact:true}).waitFor();
  await page.getByRole('link',{name:'Library',exact:true}).click();await page.getByRole('heading',{name:'Welcome back',exact:true}).waitFor();
  assert.deepEqual(errors,[]);
  const result={recorded_at:new Date().toISOString(),browser:await browser.version(),registration_login_reload_logout:true,logout_401_clears:true,six_library_operations:true,thumbnail_dimensions:thumbnail,restored_four_adjustments:saved.adjustments,saved_cube_float32_parity:true,blank_rename_rejected:true,foreign_and_missing_errors_equal:true,delete_preserved_other_record:true,signed_out_library_requests_login:true,page_errors:errors};
  fs.writeFileSync(path.join(__dirname,'library-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
