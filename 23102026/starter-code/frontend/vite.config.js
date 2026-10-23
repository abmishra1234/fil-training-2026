import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` -> http://localhost:5173, API calls are proxied to FastAPI on :8000
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
