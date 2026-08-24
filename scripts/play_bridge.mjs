#!/usr/bin/env node
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

let gplay;
try {
  gplay = require("google-play-scraper").default;
} catch {
  console.error("依赖缺失: 请先在项目根运行 npm install");
  process.exit(3);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const input = (await new Promise((resolve) => {
    let buf = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (buf += c));
    process.stdin.on("end", () => resolve(buf));
  })).trim();
  const { cmd, ...opts } = JSON.parse(input);

  if (cmd === "list") {
    const apps = await gplay.list(opts);
    process.stdout.write(JSON.stringify(apps));
  } else if (cmd === "apps") {
    const { ids, country, lang } = opts;
    const out = {};
    for (const id of ids) {
      try {
        out[id] = await gplay.app({ appId: id, country, lang });
      } catch {
        out[id] = null; // 单 app 失败容忍
      }
      await sleep(300);
    }
    process.stdout.write(JSON.stringify(out));
  } else {
    console.error(`未知指令: ${cmd}`);
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e && e.message ? e.message : String(e));
  process.exit(1);
});
