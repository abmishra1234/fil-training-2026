import { build } from "esbuild";
import { mkdir } from "node:fs/promises";

await mkdir("node_modules/.cache", { recursive: true });
await build({
  entryPoints: ["tests/chat.test.jsx"],
  outfile: "node_modules/.cache/chat-tests.mjs",
  bundle: true,
  platform: "node",
  format: "esm",
  packages: "external",
});
await import("./node_modules/.cache/chat-tests.mjs");
