#!/usr/bin/env bash
set -euo pipefail

OWNER="${OWNER:-draiagent}"
REPO="${REPO:-AI-IP-Shield}"
VERSION="${VERSION:-v0.1.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSET_DIR="${ASSET_DIR:-$ROOT/release-assets}"

command -v gh >/dev/null || { echo "ERROR: GitHub CLI (gh) is required" >&2; exit 2; }
gh auth status >/dev/null

cd "$ROOT"
python -m pytest -q
python scripts/release_check.py

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  git init -b main
  git add .
  git commit -m "Release AI-IP Shield v0.1.0 public alpha"
fi

if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  echo "Repository $OWNER/$REPO already exists; refusing to overwrite automatically." >&2
  exit 3
fi

gh repo create "$OWNER/$REPO" \
  --public \
  --description "Defensive AI-era IP protection: invisible watermarking, fingerprinting, provenance, verification, PDF tracing, and Agent Skills." \
  --source=. \
  --remote=origin \
  --push

git tag -a "$VERSION" -m "AI-IP Shield $VERSION Public Alpha"
git push origin "$VERSION"

gh release create "$VERSION" \
  "$ASSET_DIR/AI-IP-Shield-v0.1.0-release.zip#Complete release source ZIP" \
  "$ASSET_DIR/AI-IP-Shield-v0.1.0-source.tar.gz#Source TAR.GZ" \
  "$ASSET_DIR/ai_ip_shield-0.1.0-py3-none-any.whl#Python wheel" \
  "$ASSET_DIR/ai-ip-shield-skill-v0.1.0.zip#Portable Agent Skill" \
  "$ASSET_DIR/SHA256SUMS.txt#SHA-256 checksums" \
  --title "AI-IP Shield v0.1.0 — Public Alpha" \
  --notes-file "$ROOT/RELEASE-NOTES-v0.1.0.md" \
  --verify-tag \
  --latest

echo "Published: https://github.com/$OWNER/$REPO/releases/tag/$VERSION"
