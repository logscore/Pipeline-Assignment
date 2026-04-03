/**
 * Copies pipeline assets from the monorepo root into web/pipeline/ before `next build`.
 * Vercel uses Root Directory `web/`, but the clone includes the full repo, so `../..` works.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const destDir = path.resolve(__dirname, "../pipeline");

const copies = ["pipeline_prod.ipynb", "shop.db"];

fs.mkdirSync(destDir, { recursive: true });

for (const name of copies) {
  const src = path.join(repoRoot, name);
  const dest = path.join(destDir, name);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`sync-pipeline-assets: copied ${name} -> web/pipeline/`);
  } else {
    console.warn(`sync-pipeline-assets: skip (missing): ${src}`);
  }
}
