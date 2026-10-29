const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const {FRONTEND_URL, API_URL} = require('./support.cjs');
async function ready(urls = [FRONTEND_URL, API_URL + "/docs"], timeout = Number(process.env.E2E_READY_TIMEOUT_MS || 90000)) {
  if (!Number.isFinite(timeout) || timeout <= 0) throw new Error('E2E_READY_TIMEOUT_MS must be positive');
  const deadline = Date.now() + timeout;
  for (const url of urls) {
    let last;
    while (Date.now() < deadline) {
      try {
        const response = await fetch(url, {signal: AbortSignal.timeout(Math.max(1, Math.min(2000, deadline - Date.now())))});
        if (response.ok) { last = null; break; }
        last = `HTTP ${response.status}`;
      } catch (error) { last = error.message; }
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    if (last || Date.now() >= deadline) throw new Error(`Readiness timeout at ${url}: ${last || 'deadline exceeded'}. Check docker compose logs.`);
  }
}
async function main() {
  await ready();
  fs.mkdirSync('work/e2e', {recursive:true});
  for (const name of ['guest', 'library', 'studio-session']) {
    console.log(`E2E START ${name}`);
    const result = spawnSync(process.execPath, [`backend/integration/${name}.cjs`], {stdio:'inherit'});
    if (result.error || result.status !== 0) throw new Error(`E2E FAIL ${name}: ${result.error?.message || `exit ${result.status}, signal ${result.signal || 'none'}`}`);
    console.log(`E2E PASS ${name}`);
  }
  console.log('E2E PASS all scenarios');
}
module.exports = {ready};
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });
