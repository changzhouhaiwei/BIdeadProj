#!/usr/bin/env node
/**
 * 打印飞书遥控是否已接上。不输出 App Secret 和 Gateway token。
 * node status.mjs [--config <openclaw.json>]
 */
import fs from "node:fs";

const AGENT_ID = "cursor-bidead";

function parseArgs(argv) {
  let config = process.env.OPENCLAW_CONFIG_PATH || "D:\\OpenClaw\\state\\openclaw.json";
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--config") config = argv[++i] ?? "";
    else throw new Error(`未知参数: ${argv[i]}`);
  }
  return config;
}

function present(value) {
  return value ? "yes" : "no";
}

function main() {
  const configPath = parseArgs(process.argv);
  if (!fs.existsSync(configPath)) {
    console.error(`CONFIG_MISSING: ${configPath}`);
    process.exit(2);
  }
  const cfg = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const feishu = cfg.channels && cfg.channels.feishu ? cfg.channels.feishu : {};
  const accounts = feishu.accounts && typeof feishu.accounts === "object" ? feishu.accounts : {};
  const agent = (cfg.agents && cfg.agents.list ? cfg.agents.list : []).find((item) => item.id === AGENT_ID);
  const bindings = (cfg.bindings || []).filter(
    (item) => item && item.type === "acp" && item.match && item.match.channel === "feishu",
  );
  const allow = Array.isArray(feishu.allowFrom) ? feishu.allowFrom : [];

  console.log(`config=${configPath}`);
  console.log(`plugin_allowed=${(cfg.plugins && cfg.plugins.allow ? cfg.plugins.allow : []).includes("feishu")}`);
  console.log(
    `plugin_enabled=${Boolean(cfg.plugins && cfg.plugins.entries && cfg.plugins.entries.feishu && cfg.plugins.entries.feishu.enabled)}`,
  );
  console.log(`channel_enabled=${feishu.enabled !== false && Object.keys(feishu).length > 0}`);
  console.log(`connection=${feishu.connectionMode || "(unset)"}`);
  console.log(`dmPolicy=${feishu.dmPolicy || "(unset)"}`);
  console.log(`groupPolicy=${feishu.groupPolicy || "(unset)"}`);
  console.log(`appId=${present(feishu.appId || Object.values(accounts).some((item) => item && item.appId))}`);
  console.log(`appSecret=${present(feishu.appSecret || Object.values(accounts).some((item) => item && item.appSecret))}`);
  console.log(`allowFrom=${allow.length}`);
  console.log(`agent=${agent ? AGENT_ID : "missing"}`);
  console.log(`cwd=${agent && agent.runtime && agent.runtime.acp ? agent.runtime.acp.cwd : "(none)"}`);
  if (bindings.length === 0) console.log("bindings=0");
  for (const binding of bindings) {
    const peer = binding.match.peer || {};
    console.log(
      `binding agent=${binding.agentId} account=${binding.match.accountId || "default"} peer=${peer.kind || "?"}:${peer.id || "?"}`,
    );
  }
}

main();
