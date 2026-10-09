import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom no implementa URLs de objetos; el visor PDF las usa para mostrar archivos.
let objectUrlCounter = 0;
if (typeof URL.createObjectURL !== "function") {
  URL.createObjectURL = () => `blob:test/${++objectUrlCounter}`;
  URL.revokeObjectURL = () => undefined;
}

afterEach(() => {
  cleanup();
});
