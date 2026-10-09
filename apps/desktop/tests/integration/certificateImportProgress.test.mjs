import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { stripTypeScriptTypes } from "node:module";
import test from "node:test";

const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const root = new URL("../../src/", import.meta.url);
const read = async (path) => stripTypeScriptTypes(await readFile(new URL(path, root), "utf8"));
const requests = moduleUrl(await read("lib/api/documentReviews.ts"));
const jobs = moduleUrl((await read("lib/api/jobs.ts")).replace('"./documentReviews"', JSON.stringify(requests)));
const uploads = moduleUrl((await read("lib/api/documentUpload.ts")).replace('"./documentReviews"', JSON.stringify(requests)));
const api = moduleUrl(`export { getDocumentJob } from ${JSON.stringify(jobs)}; export { uploadDocument as uploadDocumentLegacy } from ${JSON.stringify(uploads)};`);
// Execute the actual hook, effects and API without adding a React toolchain to this scaffold.
const react = moduleUrl(`export const useState = (...args) => globalThis.importHooks.useState(...args);
export const useRef = (...args) => globalThis.importHooks.useRef(...args);
export const useEffect = (...args) => globalThis.importHooks.useEffect(...args);`);
const source = (await read("features/certificate-import/useCertificateImport.ts"))
  .replace('"react"', JSON.stringify(react)).replace('"../../lib/api"', JSON.stringify(api));
const { useCertificateImport } = await import(moduleUrl(source));

function mount(t, getJob) {
  const original = { fetch: globalThis.fetch, setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout };
  const cells = [], effects = [], timers = new Map();
  let cursor = 0, sequence = 0;
  globalThis.importHooks = {
    useState(initial) {
      const index = cursor++;
      if (!(index in cells)) cells[index] = initial;
      return [cells[index], (value) => { cells[index] = typeof value === "function" ? value(cells[index]) : value; }];
    },
    useRef(initial) {
      const index = cursor++;
      return cells[index] ??= { current: initial };
    },
    useEffect(effect, dependencies) {
      const index = cursor++;
      if (!cells[index] || dependencies.some((value, i) => value !== cells[index].dependencies[i])) {
        cells[index]?.cleanup?.();
        cells[index] = { dependencies };
        effects.push(() => { cells[index].cleanup = effect(); });
      }
    },
  };
  globalThis.setTimeout = (callback, delay) => {
    assert.equal(delay, 1000);
    timers.set(++sequence, callback);
    return sequence;
  };
  globalThis.clearTimeout = (id) => timers.delete(id);
  globalThis.fetch = async (url, init) => {
    if (init.method === "POST") return Response.json({ data: { document_id: 1, certificate_id: 1, job_id: 9, duplicate: false }, error: null }, { status: 202 });
    assert.equal(url, "http://localhost:8765/api/v1/jobs/9");
    return getJob(init.signal);
  };
  const render = () => {
    cursor = 0;
    const result = useCertificateImport("http://localhost:8765");
    effects.splice(0).forEach((effect) => effect());
    return result;
  };
  const unmount = () => cells.forEach((cell) => cell?.cleanup?.());
  t.after(() => { unmount(); Object.assign(globalThis, original); delete globalThis.importHooks; });
  return { render, unmount, timers,
    async start() {
      render().selectFiles([new File(["%PDF-1.7"], "mill.pdf")]);
      await render().submit();
      return render();
    },
    async tick() {
      assert.equal(timers.size, 1);
      const [id, callback] = timers.entries().next().value;
      timers.delete(id);
      await callback();
      return render();
    },
  };
}

const response = (status, progress, error_message = null) => Response.json({ data: {
  id: 9, document_id: 1, status, progress, attempts: 1, error_message,
}, error: null });

test("upload stays loading through OCR and saving; success stops polling at 100", async (t) => {
  const stages = [["queued", 0], ["running", 50], ["running", 95], ["succeeded", 100]];
  const app = mount(t, () => response(...stages.shift()));
  const initial = await app.start();
  assert.equal(initial.status, "loading");
  assert.equal(initial.uploading, false);
  for (const progress of [0, 50, 95, 100]) {
    const result = await app.tick();
    assert.equal(result.receipts[0].job.progress, progress);
    assert.equal(result.status, progress === 100 ? "success" : "loading");
  }
  assert.equal(app.timers.size, 0);
});

for (const state of ["needs_review", "needs_ocr", "failed", "cancelled"]) {
  test(`${state} stops polling and retains the explicit outcome`, async (t) => {
    const app = mount(t, () => response(state, state.startsWith("needs") ? 100 : 50, "Detalle del resultado"));
    await app.start();
    const result = await app.tick();
    assert.equal(result.status, state.startsWith("needs") ? "needs_review" : "error");
    assert.equal(result.receipts[0].job.error_message, "Detalle del resultado");
    assert.equal(app.timers.size, 0);
  });
}

test("connection failure remains visible and tracking can resume without uploading again", async (t) => {
  let unavailable = true;
  const app = mount(t, () => {
    if (unavailable) throw new Error("Sin conexión");
    return response("succeeded", 100);
  });
  await app.start();
  let result = await app.tick();
  assert.equal(result.status, "error");
  assert.equal(result.receipts[0].trackingError, "Sin conexión");
  assert.equal(app.timers.size, 0);
  unavailable = false;
  result.retryTracking(1);
  assert.equal(app.render().status, "loading");
  result = await app.tick();
  assert.equal(result.status, "success");
  assert.equal(result.receipts.length, 1);
});

test("unmount aborts an in-flight poll and ignores its late response", async (t) => {
  let finish, signal;
  const app = mount(t, (abortSignal) => {
    signal = abortSignal;
    return new Promise((resolve) => { finish = resolve; });
  });
  await app.start();
  const waiting = app.tick();
  app.unmount();
  assert.equal(signal.aborted, true);
  finish(response("succeeded", 100));
  const result = await waiting;
  assert.equal(result.receipts[0].job, null);
  assert.equal(app.timers.size, 0);
});
