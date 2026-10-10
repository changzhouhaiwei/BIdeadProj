#!/usr/bin/env node
/**
 * 把某个飞书用户的私聊绑到 cursor-bidead。
 * node bind-direct.mjs --open-id ou_xxx [--account default] [--config <openclaw.json>] [--repo <绝对路径>]
 */
import fs from "node:fs";
import path from "node:path";

const AGENT_ID = "cursor-bidead";

function parseArgs(argv) {
  const out = {
    config: process.env.OPENCLAW_CONFIG_PATH || "D:\\OpenClaw\\state\\openclaw.json",
    repo: "F:\\SelfMaj\\BIdeadProj",
    openId: "",
    account: "default",
  };
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--config") out.config = argv[++i] ?? "";
    else if (arg === "--repo") out.repo = argv[++i] ?? "";
    else if (arg === "--open-id") out.openId = argv[++i] ?? "";
    else if (arg === "--account") out.account = argv[++i] ?? "";
    else throw new Error(`未知参数: ${arg}`);
  }
  return out;
}

function isFeishuDirect(binding) {
  return (
    binding &&
    binding.type === "acp" &&
    binding.agentId === AGENT_ID &&
    binding.match &&
    binding.match.channel === "feishu" &&
    binding.match.peer &&
    binding.match.peer.kind === "direct"
  );
}

function main() {
  const args = parseArgs(process.argv);
  if (!/^ou_[A-Za-z0-9]+$/.test(args.openId)) {
    console.error("OPEN_ID 需要是 ou_ 开头的飞书 open_id");
    process.exit(2);
  }
  const repo = path.resolve(args.repo);
  if (!fs.existsSync(args.config)) {
    console.error(`CONFIG_MISSING: ${args.config}`);
    process.exit(2);
  }

  const cfg = JSON.parse(fs.readFileSync(args.config, "utf8"));
  cfg.bindings = Array.isArray(cfg.bindings) ? cfg.bindings : [];
  let binding = cfg.bindings.find(
    (item) => isFeishuDirect(item) && (item.match.accountId || "default") === args.account,
  );
  if (!binding) {
    binding = {
      type: "acp",
      agentId: AGENT_ID,
      match: {
        channel: "feishu",
        accountId: args.account,
        peer: { kind: "direct", id: args.openId },
      },
    };
    cfg.bindings.push(binding);
  }
  binding.agentId = AGENT_ID;
  binding.match.accountId = args.account;
  binding.match.peer = { kind: "direct", id: args.openId };
  binding.acp = {
    label: "cursor-feishu",
    backend: "acpx",
    mode: "persistent",
    cwd: repo,
  };

  cfg.channels = cfg.channels || {};
  const feishu = cfg.channels.feishu || {};
  feishu.dmPolicy = "allowlist";
  feishu.groupPolicy = feishu.groupPolicy || "disabled";
  const allow = new Set(Array.isArray(feishu.allowFrom) ? feishu.allowFrom : []);
  allow.add(args.openId);
  feishu.allowFrom = [...allow];
  cfg.channels.feishu = feishu;

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backup = `${args.config}.bak-feishu-bind-${stamp}`;
  fs.copyFileSync(args.config, backup);
  fs.writeFileSync(args.config, `${JSON.stringify(cfg, null, 2)}\n`);
  console.log(`BOUND open_id=${args.openId} account=${args.account}`);
  console.log(`agent=${AGENT_ID} cwd=${repo}`);
  console.log(`backup=${backup}`);
}

main();
