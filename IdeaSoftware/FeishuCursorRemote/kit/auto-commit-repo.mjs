#!/usr/bin/env node
/**
 * 飞书遥控回合结束后，提交工作区里的安全改动。
 * 用法: node auto-commit-repo.mjs --cwd <repo> [--prompt <用户原话>]
 * 只 commit，不 push。没有可提交内容时 exit 0，并打印 NO_CHANGES。
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import fs from "node:fs";

const execFileAsync = promisify(execFile);

const SECRET_BASENAMES = new Set([
  ".env",
  ".env.local",
  ".env.production",
  ".env.development",
  "credentials.json",
  "service-account.json",
  "id_rsa",
  "id_ed25519",
]);

function parseArgs(argv) {
  const out = { cwd: "", prompt: "" };
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--cwd") out.cwd = argv[++i] ?? "";
    else if (arg === "--prompt") out.prompt = argv[++i] ?? "";
    else throw new Error(`未知参数: ${arg}`);
  }
  return out;
}

function sanitizeSubject(prompt) {
  const oneLine = String(prompt || "")
    .replace(/\r?\n/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!oneLine) return "feishu task";
  return oneLine.slice(0, 72);
}

async function git(cwd, args, opts = {}) {
  const { stdout, stderr } = await execFileAsync("git", args, {
    cwd,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
    ...opts,
  });
  return {
    stdout: String(stdout ?? "").trimEnd(),
    stderr: String(stderr ?? "").trim(),
  };
}

function isSecretPath(filePath) {
  const base = path.basename(filePath).toLowerCase();
  if (SECRET_BASENAMES.has(base)) return true;
  if (base.endsWith(".pem") || base.endsWith(".key") || base.endsWith(".p12")) return true;
  if (base.includes("secret") && (base.endsWith(".json") || base.endsWith(".txt"))) return true;
  return false;
}

/** Decode git status --porcelain paths (quoted + octal escapes on Windows). */
function decodePorcelainPath(raw) {
  let s = String(raw || "").trim();
  if (s.startsWith('"') && s.endsWith('"')) {
    s = s.slice(1, -1);
    s = s.replace(/\\([0-7]{3})/g, (_, oct) => String.fromCharCode(parseInt(oct, 8)));
    s = s.replace(/\\([\\nrt"])/g, (_, ch) => {
      if (ch === "n") return "\n";
      if (ch === "r") return "\r";
      if (ch === "t") return "\t";
      return ch;
    });
  }
  return s;
}

async function main() {
  const { cwd, prompt } = parseArgs(process.argv);
  if (!cwd || !fs.existsSync(cwd)) {
    console.error(`INVALID_CWD: ${cwd}`);
    process.exit(2);
  }

  const top = await git(cwd, ["rev-parse", "--show-toplevel"]);
  const repoRoot = top.stdout;
  if (!repoRoot) {
    console.error("NOT_A_GIT_REPO");
    process.exit(2);
  }

  const status = await git(repoRoot, ["status", "--porcelain"]);
  if (!status.stdout) {
    console.log("NO_CHANGES");
    return;
  }

  const lines = status.stdout.split(/\r?\n/).filter(Boolean);
  const toAdd = [];
  const skipped = [];
  for (const line of lines) {
    const raw = line.slice(3);
    const decoded = decodePorcelainPath(raw);
    const filePath = decoded.includes(" -> ") ? decoded.split(" -> ").pop() : decoded;
    if (!filePath) continue;
    if (isSecretPath(filePath)) {
      skipped.push(filePath);
      continue;
    }
    toAdd.push(filePath);
  }

  if (toAdd.length === 0) {
    console.log(`NO_SAFE_CHANGES skipped=${skipped.join(",")}`);
    return;
  }

  await git(repoRoot, ["add", "--", ...toAdd]);

  const message = [
    `openclaw(feishu): ${sanitizeSubject(prompt)}`,
    "",
    "Auto-committed by Feishu Cursor remote after a phone-driven ACP turn.",
    skipped.length ? `Skipped secrets: ${skipped.join(", ")}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  try {
    await git(repoRoot, ["commit", "-m", message], {
      env: {
        ...process.env,
        GIT_AUTHOR_NAME: process.env.GIT_AUTHOR_NAME || "OpenClaw Feishu",
        GIT_AUTHOR_EMAIL: process.env.GIT_AUTHOR_EMAIL || "openclaw-feishu@local",
        GIT_COMMITTER_NAME: process.env.GIT_COMMITTER_NAME || "OpenClaw Feishu",
        GIT_COMMITTER_EMAIL: process.env.GIT_COMMITTER_EMAIL || "openclaw-feishu@local",
      },
    });
  } catch (err) {
    const msg = err?.stderr || err?.message || String(err);
    if (/nothing to commit/i.test(msg)) {
      console.log("NO_CHANGES");
      return;
    }
    throw err;
  }

  const head = await git(repoRoot, ["log", "-1", "--format=%h %s"]);
  const shortstat = await git(repoRoot, ["diff", "--stat", "HEAD~1..HEAD"]).catch(() => ({
    stdout: "",
  }));
  console.log(`COMMITTED ${head.stdout}`);
  if (shortstat.stdout) console.log(shortstat.stdout);
  if (skipped.length) console.log(`SKIPPED_SECRETS ${skipped.join(",")}`);
}

main().catch((err) => {
  console.error(`AUTO_COMMIT_FAILED: ${err?.stderr || err?.message || String(err)}`);
  process.exit(1);
});
