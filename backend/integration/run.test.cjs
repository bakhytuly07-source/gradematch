const {test} = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const {ready} = require('./run.cjs');
const {prepare} = require('./support.cjs');
test('readiness retries non-2xx and checks both services', async () => {
  let calls = 0;
  const server = http.createServer((req,res) => { res.writeHead(++calls === 1 ? 503 : 200); res.end(); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${server.address().port}`;
    await ready([url, url + '/docs'], 3000);
    assert.equal(calls, 3);
  } finally { await new Promise(resolve => server.close(resolve)); }
});
test('readiness failure is bounded and identifies the unavailable service', async () => {
  await assert.rejects(ready(['http://127.0.0.1:1'], 50), /Readiness timeout at http:\/\/127.0.0.1:1/);
  await assert.rejects(ready([], -1), /must be positive/);
});
test('test-only real adapter injection loads without Vite source requests', async () => {
  const vm = require('node:vm');
  const context = {window:{}, Float32Array, console};
  vm.createContext(context);
  await prepare({setDefaultTimeout() {}, on() {}, async addInitScript(fn, data) {
    context.data = data;
    vm.runInContext(`(${fn.toString()})(data)`, context);
  }});
  const adapter = new context.window.ApiService('http://localhost:8091', null);
  assert.equal(typeof adapter.renderLut, 'function');
  assert.equal(typeof adapter.saveLook, 'function');
});
