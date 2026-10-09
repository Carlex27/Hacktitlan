import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { stripTypeScriptTypes } from "node:module";
import test from "node:test";

const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const apiRoot = new URL("../../src/lib/api/", import.meta.url);
const requests = moduleUrl(stripTypeScriptTypes(await readFile(new URL("documentReviews.ts", apiRoot), "utf8")));
const source = stripTypeScriptTypes(await readFile(new URL("documentUpload.ts", apiRoot), "utf8"));
const { uploadDocument } = await import(moduleUrl(source.replace('"./documentReviews"', JSON.stringify(requests))));

test("upload sends actual bytes with browser multipart and returns the typed receipt", async () => {
  const originalFetch = globalThis.fetch;
  const receipt = { document_id: 1, certificate_id: 2, job_id: 3, duplicate: false };
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "http://localhost:8765/api/v1/documents");
      assert.equal(init.method, "POST");
      assert.equal(init.headers, undefined);
      const file = init.body.get("file");
      assert.equal(file.name, "mill.xlsx");
      assert.equal(await file.text(), "source bytes");
      return Response.json({ data: receipt, error: null }, { status: 202 });
    };
    assert.deepEqual(await uploadDocument("http://localhost:8765/", new File(["source bytes"], "mill.xlsx")), receipt);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("server rejection remains visible to the import flow", async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => Response.json({ data: null, error: { message: "Libro inválido" } }, { status: 400 });
    await assert.rejects(uploadDocument("", new File(["bad"], "bad.xlsx")), /Libro inválido/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
