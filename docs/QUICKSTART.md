# Quickstart

## 1. Install

```bash
python -m pip install -e .
aipshield doctor
```

## 2. Protect

```bash
aipshield protect input.png protected.png --registry data/registry.sqlite3
```

PDF:

```bash
aipshield protect input.pdf protected.pdf --registry data/registry.sqlite3
```

## 3. Verify immediately

```bash
aipshield verify protected.png \
  --registry data/registry.sqlite3 \
  --report-json verify.json \
  --report-md verify.md
```

## 4. Add trusted provenance when needed

```bash
aipshield provenance-keygen --private-key signing.pem --public-key signing.pub.pem
aipshield provenance-trust signing.pub.pem --trust-store trust-store.json --label publisher
```

Keep `signing.pem` outside Git.

## 5. Install the Agent Skill

```bash
aipshield skill-install --host both --scope project
```

Then use the installed `ai-ip-shield` Skill in Codex or Claude Code.

For ChatGPT, export the portable ZIP and upload it in the Skills UI when Skills/upload is enabled for your account or workspace:

```bash
aipshield skill-export --output ai-ip-shield-skill-v0.1.0.zip
```
