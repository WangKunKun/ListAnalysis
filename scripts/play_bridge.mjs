#!/usr/bin/env node
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
const require = createRequire(import.meta.url);

let gplay;
try {
  gplay = require("google-play-scraper").default;
} catch {
  console.error("依赖缺失: 请先在项目根运行 npm install");
  process.exit(3);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// search 输出协议:数组元素只保留 appId/title/developer 三字段。
// Python 侧 fetch.adapters.play.normalize_search 依赖此格式,
// 契约测试见 tests/test_play_bridge.py::TestSearchOutputContract。
export function formatSearchResults(results) {
  return results.map(({ appId, title, developer }) => ({ appId, title, developer }));
}

// reviews 输出协议:平铺 [{score, text}, ...]。
// Python 侧 fetch.reviews.normalize_play_reviews 依赖此格式,
// 契约测试见 tests/test_play_bridge.py::TestSearchOutputContract。
export function formatReviews(data) {
  return (data || []).map(({ score, text }) => ({ score, text: text || "" }));
}

// 代理支持:got@11 不读代理环境变量,须显式传 agent。
// PLAY_PROXY 优先于 HTTPS_PROXY;未设置时 requestOpts 为空对象(行为与旧版一致)
let requestOpts = {};
const proxyUrl = process.env.PLAY_PROXY || process.env.HTTPS_PROXY || "";
if (proxyUrl) {
  try {
    const { HttpsProxyAgent } = require("hpagent");
    requestOpts = { agent: { https: new HttpsProxyAgent({ proxy: proxyUrl }) } };
  } catch {
    console.error("代理配置失败: hpagent 未安装,请在项目根运行 npm install");
    process.exit(3);
  }
}

async function main() {
  const input = (await new Promise((resolve) => {
    let buf = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (buf += c));
    process.stdin.on("end", () => resolve(buf));
  })).trim();
  const { cmd, ...opts } = JSON.parse(input);

  if (cmd === "list") {
    const apps = await gplay.list({ ...opts, requestOptions: requestOpts });
    process.stdout.write(JSON.stringify(apps));
  } else if (cmd === "apps") {
    const { ids, country, lang } = opts;
    const out = {};
    for (const id of ids) {
      try {
        out[id] = await gplay.app({ appId: id, country, lang,
                                    requestOptions: requestOpts });
      } catch {
        out[id] = null; // 单 app 失败容忍
      }
      await sleep(300);
    }
    process.stdout.write(JSON.stringify(out));
  } else if (cmd === "search") {
    const results = await gplay.search({ ...opts, requestOptions: requestOpts });
    process.stdout.write(JSON.stringify(formatSearchResults(results)));
  } else if (cmd === "reviews") {
    const r = await gplay.reviews({ ...opts, requestOptions: requestOpts });
    process.stdout.write(JSON.stringify(formatReviews(r.data)));
  } else {
    console.error(`未知指令: ${cmd}`);
    process.exit(1);
  }
}

// 仅直接执行时跑 CLI;被 import(契约测试)时只暴露纯函数
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((e) => {
    console.error(e && e.message ? e.message : String(e));
    process.exit(1);
  });
}
