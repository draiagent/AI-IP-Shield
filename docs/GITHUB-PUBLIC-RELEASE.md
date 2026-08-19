# GitHub Public Release Runbook — v0.1.0

This runbook publishes `draiagent/AI-IP-Shield` as a public repository and creates the `v0.1.0` release.

## Pre-release gate

```bash
python -m pytest -q
python scripts/release_check.py
```

Required release assets:

```text
AI-IP-Shield-v0.1.0-release.zip
AI-IP-Shield-v0.1.0-source.tar.gz
ai_ip_shield-0.1.0-py3-none-any.whl
ai-ip-shield-skill-v0.1.0.zip
SHA256SUMS.txt
```

## Automated publication

Authenticate GitHub CLI first:

```bash
gh auth login
```

Then run:

```bash
ASSET_DIR=/absolute/path/to/release-assets \
  bash scripts/publish_github.sh
```

The script deliberately refuses to overwrite an existing repository.

## Post-release verification

```bash
tmp="$(mktemp -d)"
git clone https://github.com/draiagent/AI-IP-Shield.git "$tmp/AI-IP-Shield"
cd "$tmp/AI-IP-Shield"
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
aipshield version
aipshield doctor
python -m pytest -q
python scripts/release_check.py
```

Release asset verification:

```bash
gh release download v0.1.0 -R draiagent/AI-IP-Shield -D release-download
cd release-download
sha256sum -c SHA256SUMS.txt
```
