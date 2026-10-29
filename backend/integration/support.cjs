const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('../../frontend/node_modules/typescript');
const FRONTEND_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8091';
// Compile the existing real adapter and its imports for injection into a built
// frontend. No HTTP requests for Vite source modules or alternate app server.
function adapterBundle() {
  const modules = {};
  const dir = path.resolve(__dirname, '../../frontend/src/services');
  for (const name of ['api', 'types', 'validation', 'mapping']) {
    modules['./' + name] = ts.transpileModule(fs.readFileSync(path.join(dir, name + '.ts'), 'utf8'), {
      compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
    }).outputText;
  }
  return {modules};
}
async function launch() {
  const browser = await chromium.launch({headless: true, channel: 'chromium'});
  browser.e2eAccounts = [];
  const close = browser.close.bind(browser);
  browser.close = async () => {
    try {
      // Revoke still-signed-in UI sessions before opening temporary cleanup sessions.
      for (const context of browser.contexts()) for (const page of context.pages()) {
        const token = await page.evaluate(api => sessionStorage.getItem(`gradematch.token:${api}`), API_URL).catch(() => null);
        if (token) await fetch(API_URL + '/api/auth/logout', {method:'POST', headers:{Authorization:`Bearer ${token}`}, signal:AbortSignal.timeout(10000)});
      }
      for (const credentials of browser.e2eAccounts) {
        const response = await fetch(API_URL + '/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(credentials), signal:AbortSignal.timeout(10000)});
        if (!response.ok) throw new Error(`Cleanup login failed: ${response.status}`);
        const {access_token} = await response.json();
        const headers = {Authorization:`Bearer ${access_token}`};
        try {
          const listed = await fetch(API_URL + '/api/looks', {headers, signal:AbortSignal.timeout(10000)});
          if (!listed.ok) throw new Error(`Cleanup list failed: ${listed.status}`);
          for (const look of await listed.json()) {
            const deleted = await fetch(API_URL + '/api/looks/' + encodeURIComponent(look.id), {method:'DELETE', headers, signal:AbortSignal.timeout(10000)});
            if (!deleted.ok) throw new Error(`Cleanup delete failed: ${deleted.status}`);
          }
        } finally {
          await fetch(API_URL + '/api/auth/logout', {method:'POST', headers, signal:AbortSignal.timeout(10000)});
        }
      }
    } finally { await close(); }
  };
  return browser;
}
async function prepare(page) {
  fs.mkdirSync(path.resolve(__dirname, '../../work/e2e'), {recursive:true});
  page.setDefaultTimeout(15000);
  page.on('response', response => {
    if (response.url().endsWith('/api/auth/register') && response.status() === 201)
      page.context().browser().e2eAccounts.push(response.request().postDataJSON());
  });
  // Load the actual adapter with a small CommonJS loader. Mapping's zod import
  // is supplied by its installed CommonJS files, included recursively.
  const modules = adapterBundle().modules;
  const zodRoot = path.dirname(require.resolve('../../frontend/node_modules/zod/package.json'));
  function include(file) {
    const key = file;
    if (modules[key]) return;
    const source = fs.readFileSync(file, 'utf8');
    modules[key] = source.replace(/require\(["'](\.[^"']+)["']\)/g, (_, rel) => {
      const resolved = require.resolve(path.resolve(path.dirname(file), rel));
      include(resolved); return `require(${JSON.stringify(resolved)})`;
    });
  }
  const zodEntry = require.resolve(zodRoot); include(zodEntry);
  await page.addInitScript(({modules, zodEntry, api}) => {
    const cache = {};
    function load(key) {
      if (key === 'zod') key = zodEntry;
      if (!cache[key]) {
        const module = {exports: {}}; cache[key] = module;
        new Function('require', 'module', 'exports', modules[key])(load, module, module.exports);
      }
      return cache[key].exports;
    }
    window.ApiService = load('./api').ApiService;
    window.e2eApiUrl = api;
  }, {modules, zodEntry, api: API_URL});
}
module.exports = {launch, prepare, FRONTEND_URL, API_URL};
