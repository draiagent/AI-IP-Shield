# Installation

## Python CLI

From the repository:

```bash
python -m pip install -e .
aipshield doctor
```

From the built wheel:

```bash
python -m pip install dist/ai_ip_shield-0.1.0-py3-none-any.whl
aipshield doctor
```

`aipshield doctor` is the readiness check. The lightweight commands `version`, `doctor`, `skill-install`, and `skill-export` can run before media dependencies are fully available, which makes installation failures diagnosable instead of crashing at CLI import time.

## Codex

Repository scope:

```bash
aipshield skill-install --host codex --scope project
```

This installs the Skill under `.agents/skills/ai-ip-shield/`.

User scope:

```bash
aipshield skill-install --host codex --scope user
```

Then invoke explicitly with `$ai-ip-shield`/the Codex Skill picker, or let Codex select it when the task matches its description.

## Claude Code

Repository scope:

```bash
aipshield skill-install --host claude --scope project
```

This installs the Skill under `.claude/skills/ai-ip-shield/`.

User scope:

```bash
aipshield skill-install --host claude --scope user
```

Claude Code discovers the Skill from the project/user Skill location.

## ChatGPT

Export the portable Skill package:

```bash
aipshield skill-export --output ai-ip-shield-skill-v0.1.0.zip
```

On a ChatGPT account/workspace where Skills and Skill upload are enabled, use the ChatGPT Skills UI and upload the ZIP from your computer. ChatGPT Skills availability and workspace permissions are controlled by the current ChatGPT plan/workspace configuration, so the CLI does not pretend to install directly into ChatGPT.

The same ZIP follows the Agent Skills directory convention: one top-level `ai-ip-shield/` directory containing `SKILL.md` plus supporting resources.

## Build the wheel

Normal connected build environment:

```bash
python -m pip wheel . --no-deps -w dist
```

If build isolation cannot download build dependencies (for example, an offline CI/sandbox) but the required build backend is already installed:

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
```
