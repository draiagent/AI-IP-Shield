# Agent Integration

## OpenAI ChatGPT

AI-IP Shield is packaged in the Agent Skills open directory format: `SKILL.md` at the Skill root, progressive-disclosure reference files, and optional OpenAI metadata under `agents/openai.yaml`.

Portable package:

```text
ai-ip-shield/
├── SKILL.md
├── agents/openai.yaml
└── references/
```

Generate it with:

```bash
aipshield skill-export --output ai-ip-shield-skill-v0.1.0.zip
```

ChatGPT installation is performed through ChatGPT's Skills UI when the user's account/workspace has Skills and uploading enabled. It is deliberately not represented as a local filesystem install by AI-IP Shield.

## OpenAI Codex

Repo-local copy:

```text
.agents/skills/ai-ip-shield/
├── SKILL.md
├── references/
└── agents/openai.yaml
```

Install:

```bash
aipshield skill-install --host codex --scope project
```

`AGENTS.md` supplies repository-wide invariants. The Skill supplies task-specific protect/verify/provenance/Attack Lab workflows.

## Claude Code

Project copy:

```text
.claude/skills/ai-ip-shield/
├── SKILL.md
└── references/
```

Install:

```bash
aipshield skill-install --host claude --scope project
```

`CLAUDE.md` holds repository-wide engineering invariants; the Skill holds task-specific workflows. The extra OpenAI metadata file is inert for Claude Code and is kept only so mirrored Skill packages remain byte-consistent.

## Invocation behavior

The Skill `description` intentionally includes protection, watermark, fingerprint, provenance, trace, verification, leaked-copy, Do Not Train, and robustness trigger terms. It excludes unrelated document-editing terms so the Skill should not activate on ordinary PDF tasks.

## Deterministic boundary

The Skill instructs the agent to call the `aipshield` CLI rather than reproduce the watermarking algorithm in natural language. The agent decides **when and why** to invoke protection; the CLI performs **deterministic embed/verify/report operations**.
