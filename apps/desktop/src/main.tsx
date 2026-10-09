import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app";
import "@/styles/globals.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("No se encontró el elemento raíz #root");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
