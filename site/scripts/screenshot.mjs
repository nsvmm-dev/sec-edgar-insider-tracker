#!/usr/bin/env node
/**
 * Visual QA screenshots of the built site (site/dist/), at a real CSS-pixel
 * viewport width -- no browser installation beyond a local Chrome/Chromium.
 *
 * Why this exists: headless Chrome's `--window-size` flag is silently
 * clamped to a much larger minimum on at least one dev machine used on this
 * project (a requested 390px viewport rendered as ~500px, with the PNG then
 * cropped to 390px -- content that fit fine at the real width looked
 * "overflowing" in the screenshot). This script drives Chrome over the
 * DevTools Protocol and sets the viewport with
 * `Emulation.setDeviceMetricsOverride`, which is not subject to that floor.
 *
 * Usage:
 *   npm run build
 *   node scripts/screenshot.mjs <path> [outfile] [width] [height]
 *
 * Examples:
 *   node scripts/screenshot.mjs /                       shot.png   390 844
 *   node scripts/screenshot.mjs /articles/some-slug/     article.png 1440 900
 *
 * <path> is resolved against a local static server for site/dist/ (started
 * and stopped automatically). Requires Chrome/Chromium; override the binary
 * with CHROME_PATH if it isn't at one of the default install locations.
 *
 * Git Bash note: a bare "/" argument gets silently rewritten to the Git
 * install path by MSYS's automatic POSIX-to-Windows path conversion. Pass
 * "./" for the homepage instead (both resolve identically against the base
 * URL); path arguments that start with a segment name, e.g. "/weekly/", are
 * not affected.
 */
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.join(__dirname, "..", "dist");

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".xml": "application/xml",
};

function findChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  throw new Error(
    "Could not find a Chrome/Chromium binary. Set CHROME_PATH to its executable.",
  );
}

async function serveDist(port) {
  const server = createServer(async (req, res) => {
    let file = decodeURIComponent(req.url.split("?")[0]);
    if (file.endsWith("/")) file += "index.html";
    let full = path.join(DIST_DIR, file);
    try {
      const data = await readFile(full);
      const ext = path.extname(full);
      res.writeHead(200, { "content-type": CONTENT_TYPES[ext] || "application/octet-stream" });
      res.end(data);
    } catch {
      try {
        const data = await readFile(path.join(DIST_DIR, "404.html"));
        res.writeHead(404, { "content-type": "text/html; charset=utf-8" });
        res.end(data);
      } catch {
        res.writeHead(404);
        res.end("not found");
      }
    }
  });
  await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
  return server;
}

async function waitForCdp(port, timeoutMs = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("Chrome DevTools endpoint never became reachable");
}

async function main() {
  const [, , urlPath = "/", outfile = "shot.png", widthArg = "390", heightArg = "844"] =
    process.argv;
  const width = Number(widthArg);
  const height = Number(heightArg);
  const httpPort = 8000 + Math.floor(Math.random() * 1000);
  const cdpPort = 9200 + Math.floor(Math.random() * 300);

  const server = await serveDist(httpPort);
  const userDataDir = await mkdtemp(path.join(tmpdir(), "cdp-shot-"));
  const chrome = spawn(
    findChrome(),
    [
      "--headless=new",
      "--disable-gpu",
      `--remote-debugging-port=${cdpPort}`,
      `--user-data-dir=${userDataDir}`,
    ],
    { stdio: "ignore" },
  );

  try {
    await waitForCdp(cdpPort);

    const target = await (
      await fetch(`http://127.0.0.1:${cdpPort}/json/new?about:blank`, { method: "PUT" })
    ).json();
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));

    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        pending.get(msg.id)(msg.result);
        pending.delete(msg.id);
      }
    });
    const send = (method, params = {}) => {
      const msgId = ++id;
      return new Promise((resolve) => {
        pending.set(msgId, resolve);
        ws.send(JSON.stringify({ id: msgId, method, params }));
      });
    };

    await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 2,
      mobile: width < 768,
    });

    const loadPromise = new Promise((resolve) => {
      const handler = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.method === "Page.loadEventFired") {
          ws.removeEventListener("message", handler);
          resolve();
        }
      };
      ws.addEventListener("message", handler);
    });

    const fullUrl = new URL(urlPath, `http://127.0.0.1:${httpPort}`).href;
    await send("Page.navigate", { url: fullUrl });
    await Promise.race([loadPromise, new Promise((r) => setTimeout(r, 8000))]);
    await new Promise((r) => setTimeout(r, 300)); // let webfonts/layout settle

    const shot = await send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false,
    });
    const { writeFile } = await import("node:fs/promises");
    await writeFile(outfile, Buffer.from(shot.data, "base64"));
    console.log(`wrote ${outfile} (${width}x${height} viewport, ${fullUrl})`);

    ws.close();
  } finally {
    chrome.kill();
    server.close();
    await rm(userDataDir, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
