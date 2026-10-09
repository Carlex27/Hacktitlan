import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom no implementa URLs de objetos; el visor PDF las usa para mostrar archivos.
// Radix Select usa estas APIs del navegador que jsdom no implementa.
HTMLElement.prototype.scrollIntoView = () => undefined;
HTMLElement.prototype.hasPointerCapture = () => false;
HTMLElement.prototype.releasePointerCapture = () => undefined;
let objectUrlCounter = 0;
if (typeof URL.createObjectURL !== "function") {
  URL.createObjectURL = () => `blob:test/${++objectUrlCounter}`;
  URL.revokeObjectURL = () => undefined;
}

afterEach(() => {
  cleanup();
});
