#!/usr/bin/env node
/**
 * 把飞书遥控所需的代理和通道策略合并进现有 openclaw.json。
 * 不写入 App Secret，不改微信通道，不改已有 cursor 代理的 cwd。
 *
 * node apply-config.mjs [--config <openclaw.json>] [--repo <绝对路径>] [--dry-run]
 */
import fs from "node:fs";
import path from "node:path";

const AGENT_ID = "cursor-bidead";

function parseArgs(argv) {
  const out = {
    config: process.env.OPENCLAW_CONFIG_PATH || "D:\\OpenClaw\\state\\openclaw.json",
    repo: "F:\\SelfMaj\\BIdeadProj",
    dryRun: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--config") out.config = argv[++i] ?? "";
    else if (arg === "--repo") out.repo = argv[++i] ?? "";
    else if (arg === "--dry-run") out.dryRun = true;
    else throw new Error(`未知参数: ${arg}`);
  }
  return out;
}

function chatToolsOff() {
  return {
    doc: false,
    chat: false,
    wiki: false,
    drive: false,
    perm: false,
    scopes: true,
    bitable: false,
  };
}

function apply(cfg, repo) {
  cfg.plugins = cfg.plugins || {};
  cfg.plugins.allow = Array.isArray(cfg.plugins.allow) ? cfg.plugins.allow : [];
  if (!cfg.plugins.allow.includes("feishu")) cfg.plugins.allow.push("feishu");
  cfg.plugins.entries = cfg.plugins.entries || {};
  const feishuPlugin = cfg.plugins.entries.feishu || {};
  feishuPlugin.enabled = true;
  cfg.plugins.entries.feishu = feishuPlugin;

  cfg.acp = cfg.acp || {};
  cfg.acp.enabled = true;
  if (!cfg.acp.backend) cfg.acp.backend = "acpx";
  cfg.acp.allowedAgents = Array.isArray(cfg.acp.allowedAgents) ? cfg.acp.allowedAgents : [];
  if (!cfg.acp.allowedAgents.includes("cursor")) cfg.acp.allowedAgents.push("cursor");

  cfg.agents = cfg.agents || {};
  cfg.agents.list = Array.isArray(cfg.agents.list) ? cfg.agents.list : [];
  let agent = cfg.agents.list.find((item) => item && item.id === AGENT_ID);
  if (!agent) {
    agent = { id: AGENT_ID };
    cfg.agents.list.push(agent);
  }
  agent.runtime = {
    type: "acp",
    acp: {
      agent: "cursor",
      backend: "acpx",
      mode: "persistent",
      cwd: repo,
    },
  };

  cfg.channels = cfg.channels || {};
  const feishu = cfg.channels.feishu || {};
  if (feishu.enabled === undefined) feishu.enabled = true;
  if (!feishu.domain) feishu.domain = "feishu";
  if (!feishu.connectionMode) feishu.connectionMode = "websocket";
  if (!feishu.dmPolicy) feishu.dmPolicy = "pairing";
  if (!feishu.groupPolicy) feishu.groupPolicy = "disabled";
  if (!feishu.tools) feishu.tools = chatToolsOff();
  cfg.channels.feishu = feishu;
  return cfg;
}

function main() {
  const args = parseArgs(process.argv);
  const repo = path.resolve(args.repo);
  if (!fs.existsSync(repo)) {
    console.error(`REPO_MISSING: ${repo}`);
    process.exit(2);
  }
  if (!fs.existsSync(args.config)) {
    console.error(`CONFIG_MISSING: ${args.config}`);
    process.exit(2);
  }

  const cfg = JSON.parse(fs.readFileSync(args.config, "utf8"));
  apply(cfg, repo);
  const text = `${JSON.stringify(cfg, null, 2)}\n`;

  if (args.dryRun) {
    console.log(`DRY_RUN agent=${AGENT_ID}`);
    console.log(`cwd=${repo}`);
    console.log(`config=${args.config}`);
    return;
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backup = `${args.config}.bak-feishu-${stamp}`;
  fs.copyFileSync(args.config, backup);
  fs.writeFileSync(args.config, text);
  console.log(`APPLIED backup=${backup}`);
  console.log(`agent=${AGENT_ID}`);
  console.log(`cwd=${repo}`);
}

main();
