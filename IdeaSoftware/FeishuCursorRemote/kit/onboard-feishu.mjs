#!/usr/bin/env node
/**
 * 用飞书扫码创建机器人，写进本机 OpenClaw，并绑到 cursor-bidead。
 * node onboard-feishu.mjs
 * 密钥只写入 OPENCLAW_CONFIG_PATH，不打印。
 */
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CONFIG = process.env.OPENCLAW_CONFIG_PATH || "D:\\OpenClaw\\state\\openclaw.json";
const STATE = "D:\\OpenClaw\\state\\feishu-onboard.json";
const QR_PNG = "D:\\OpenClaw\\state\\feishu-onboard-qr.png";
const RESULT = "D:\\OpenClaw\\state\\feishu-onboard-result.txt";
const QR_PKG = "D:\\OpenClaw\\state\\feishu-onboard-tools\\package.json";
const NODE_EXE = "D:\\OpenClaw\\deps\\node-v24.18.1-win-x64\\node.exe";
const OPENCLAW_MJS = "C:\\Users\\Lenovo\\AppData\\Roaming\\npm\\node_modules\\openclaw\\openclaw.mjs";
const KIT = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const REPO = "F:\\SelfMaj\\BIdeadProj";
const ACCOUNTS = "https://accounts.feishu.cn/oauth/v1/app/registration";

function log(line) {
  fs.writeSync(1, `${line}\n`);
}

async function post(body) {
  const response = await fetch(ACCOUNTS, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(body),
    signal: AbortSignal.timeout(15000),
  });
  const text = await response.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error(`飞书注册接口返回的不是 JSON（HTTP ${response.status}）`);
  }
  if (!response.ok) throw new Error(`飞书注册接口 HTTP ${response.status}`);
  return json;
}

function readConfig() {
  return JSON.parse(fs.readFileSync(CONFIG, "utf8"));
}

function writeConfig(cfg) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backup = `${CONFIG}.bak-feishu-onboard-${stamp}`;
  fs.copyFileSync(CONFIG, backup);
  fs.writeFileSync(CONFIG, `${JSON.stringify(cfg, null, 2)}\n`);
  return backup;
}

function runNode(script, args) {
  const result = spawnSync(NODE_EXE, [script, ...args], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.status !== 0) {
    const detail = `${result.stdout || ""}\n${result.stderr || ""}`.trim();
    throw new Error(`${path.basename(script)} 失败: ${detail}`);
  }
}

function runOpenclaw(args) {
  const result = spawnSync(NODE_EXE, [OPENCLAW_MJS, ...args], {
    encoding: "utf8",
    windowsHide: true,
    env: {
      ...process.env,
      PATH: `D:\\OpenClaw\\deps\\node-v24.18.1-win-x64;${process.env.PATH || ""}`,
      OPENCLAW_HOME: "D:\\OpenClaw",
      OPENCLAW_STATE_DIR: "D:\\OpenClaw\\state",
      OPENCLAW_CONFIG_PATH: CONFIG,
    },
  });
  return {
    code: result.status ?? 1,
    out: `${result.stdout || ""}\n${result.stderr || ""}`.trim(),
  };
}

function applyCredentials(appId, appSecret, openId, domain) {
  const cfg = readConfig();
  const weixin = JSON.stringify(cfg.channels?.["openclaw-weixin"] ?? null);
  const cursor = JSON.stringify((cfg.agents?.list || []).find((item) => item.id === "cursor") ?? null);
  const weixinBindings = JSON.stringify(
    (cfg.bindings || []).filter((item) => item?.match?.channel === "openclaw-weixin"),
  );

  cfg.channels = cfg.channels || {};
  const feishu = cfg.channels.feishu || {};
  feishu.enabled = true;
  feishu.domain = domain || "feishu";
  feishu.connectionMode = "websocket";
  feishu.appId = appId;
  feishu.appSecret = appSecret;
  feishu.groupPolicy = "disabled";
  if (openId) {
    feishu.dmPolicy = "allowlist";
    const allow = new Set(Array.isArray(feishu.allowFrom) ? feishu.allowFrom : []);
    allow.add(openId);
    feishu.allowFrom = [...allow];
  } else if (!feishu.dmPolicy) {
    feishu.dmPolicy = "pairing";
  }
  feishu.tools = {
    doc: false,
    chat: false,
    wiki: false,
    drive: false,
    perm: false,
    scopes: true,
    bitable: false,
  };
  cfg.channels.feishu = feishu;

  if (JSON.stringify(cfg.channels["openclaw-weixin"] ?? null) !== weixin) throw new Error("微信通道被改动，已中止");
  if (JSON.stringify((cfg.agents?.list || []).find((item) => item.id === "cursor") ?? null) !== cursor) {
    throw new Error("微信 Cursor 代理被改动，已中止");
  }
  if (JSON.stringify((cfg.bindings || []).filter((item) => item?.match?.channel === "openclaw-weixin")) !== weixinBindings) {
    throw new Error("微信绑定被改动，已中止");
  }

  return writeConfig(cfg);
}

async function finish(appId, appSecret, openId, domain) {
  const backup = applyCredentials(appId, appSecret, openId, domain);
  log(`CREDENTIALS_WRITTEN backup=${backup} openId=${openId ? "yes" : "no"}`);
  runNode(path.join(KIT, "apply-config.mjs"), ["--repo", REPO]);
  if (openId && /^ou_[A-Za-z0-9]+$/.test(openId)) {
    runNode(path.join(KIT, "bind-direct.mjs"), ["--repo", REPO, "--open-id", openId]);
    log("BINDING_WRITTEN");
  } else {
    log("BINDING_SKIPPED");
  }
  const valid = runOpenclaw(["config", "validate"]);
  if (valid.code !== 0) throw new Error(`config validate 失败: ${valid.out}`);
  log("CONFIG_VALID");
  const restarted = runOpenclaw(["gateway", "restart"]);
  log(`GATEWAY_RESTART code=${restarted.code}`);
  if (restarted.code !== 0) throw new Error(`gateway restart 失败: ${restarted.out}`);
  const status = runOpenclaw(["channels", "status", "--probe"]);
  const text = status.out.replace(/appSecret["']?\s*[:=]\s*["'][^"']+["']/gi, "appSecret=(hidden)");
  log(text);
  fs.writeFileSync(RESULT, openId ? "BOUND\n" : "CREDENTIALS_ONLY\n");
  fs.rmSync(STATE, { force: true });
  log(openId ? "ONBOARD_DONE" : "ONBOARD_DONE_NO_OPEN_ID");
}

async function main() {
  const init = await post({ action: "init" });
  const methods = init.supported_auth_methods;
  const methodList = Array.isArray(methods) ? methods : Object.values(methods || {});
  if (!methodList.includes("client_secret")) throw new Error("当前飞书环境不支持 client_secret 注册");

  const begin = await post({
    action: "begin",
    archetype: "PersonalAgent",
    auth_method: "client_secret",
    request_user_info: "open_id",
  });
  const qrUrl = new URL(begin.verification_uri_complete);
  qrUrl.searchParams.set("from", "oc_onboard");
  qrUrl.searchParams.set("tp", "ob_cli_app");
  const url = qrUrl.toString();
  fs.writeFileSync(
    STATE,
    JSON.stringify({
      deviceCode: begin.device_code,
      interval: begin.interval || 5,
      expiresIn: begin.expires_in || 3600,
      startedAt: new Date().toISOString(),
    }),
  );

  const require = createRequire(QR_PKG);
  const QRCode = require("qrcode");
  await QRCode.toFile(QR_PNG, url, { width: 720, margin: 2, errorCorrectionLevel: "M" });
  log(`QR_READY ${QR_PNG}`);
  log("WAITING_FOR_SCAN");

  const intervalSec = Number(begin.interval) > 0 ? Number(begin.interval) : 5;
  const deadline = Date.now() + (Number(begin.expires_in) > 0 ? Number(begin.expires_in) : 3600) * 1000;
  let domain = "feishu";
  let domainSwitched = false;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, intervalSec * 1000));
    let poll;
    try {
      poll = await post({
        action: "poll",
        device_code: begin.device_code,
        tp: "ob_cli_app",
      });
    } catch {
      continue;
    }
    const brand = poll.user_info?.tenant_brand;
    if (!domainSwitched && brand === "lark") {
      domain = "lark";
      domainSwitched = true;
      continue;
    }
    if (poll.client_id && poll.client_secret) {
      await finish(poll.client_id, poll.client_secret, poll.user_info?.open_id || "", domain);
      return;
    }
    if (poll.error === "authorization_pending") continue;
    if (poll.error === "slow_down") {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      continue;
    }
    if (poll.error === "access_denied") {
      fs.writeFileSync(RESULT, "DENIED\n");
      log("ONBOARD_FAILED denied");
      process.exit(1);
    }
    if (poll.error === "expired_token") {
      fs.writeFileSync(RESULT, "EXPIRED\n");
      log("ONBOARD_FAILED expired");
      process.exit(1);
    }
    if (poll.error) {
      fs.writeFileSync(RESULT, "ERROR\n");
      log(`ONBOARD_FAILED ${poll.error}`);
      process.exit(1);
    }
  }
  fs.writeFileSync(RESULT, "TIMEOUT\n");
  log("ONBOARD_FAILED timeout");
  process.exit(1);
}

main().catch((err) => {
  fs.writeFileSync(RESULT, "ERROR\n");
  log(`ONBOARD_FAILED ${err?.message || err}`);
  process.exit(1);
});
