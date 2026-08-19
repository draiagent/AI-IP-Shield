# AI-IP Shield v0.1.0 — Public Alpha

[繁體中文](#繁體中文) · [English](#english)

## 繁體中文

### 首次公開 Alpha

AI-IP Shield v0.1.0 是第一個可公開測試的完整版本，整合圖片與 PDF 隱形追蹤、Fingerprint Registry、SHA-256 完整性、Ed25519 來源證明、Attack Lab、Evidence Fusion，以及 ChatGPT / Codex / Claude Code Agent Skill。

### 包含功能

- JPG / PNG 指紋與隱形浮水印保護
- PDF raster-visual 逐頁追蹤
- SQLite Fingerprint Registry
- SHA-256 exact integrity check
- Ed25519 sidecar provenance + local trust store
- optional C2PA adapter
- Do Not Train policy assertion
- 可重現 Attack Lab / release gates
- Codex / Claude Code repo/user scoped Skill
- ChatGPT portable Skill ZIP
- CLI `protect`、`verify`、`attack`、provenance、Skill 管理命令

### 已驗證 baseline

固定 image engine 曾通過專案定義的 100-image / 500-negative-control release gate；PDF adapter 曾通過 20-PDF / 100-page gate。這些結果是專案內部工程 benchmark，不是第三方安全認證，也不代表所有真實攻擊都能達到 100%。

### 已知限制

- PDF V0.1 採 raster-visual 模式，不保留原生文字／向量語意。
- Native C2PA smoke test 仍依執行環境而定。
- PixelSeal 仍是 challenger engine，待真實 checkpoint benchmark。
- Camera capture、Perspective、AI editing / regeneration 與 anti-distillation 為後續測試範圍。

## English

### First public alpha

AI-IP Shield v0.1.0 is the first public testing release combining image/PDF invisible traceability, a fingerprint registry, SHA-256 integrity checks, Ed25519 provenance, Attack Lab, evidence fusion, and portable Agent Skills for ChatGPT / Codex / Claude Code.

### Included

- JPG / PNG fingerprint and invisible watermark protection
- PDF raster-visual page-level traceability
- SQLite fingerprint registry
- SHA-256 exact integrity checks
- Ed25519 sidecar provenance and local trust store
- optional C2PA adapter
- Do Not Train policy assertion support
- reproducible Attack Lab and release gates
- repo/user-scoped Codex and Claude Code Skills
- portable ChatGPT Skill ZIP
- CLI for protect, verify, attack, provenance, and Skill management

### Validated baseline

The pinned image engine previously passed the project's defined 100-image / 500-negative-control release gate. The PDF adapter previously passed the defined 20-PDF / 100-page gate. These results are internal engineering benchmarks, not third-party security certifications and not guarantees of 100% robustness against every real-world attack.

### Known limitations

- PDF v0.1 is raster-visual and does not preserve native text/vector semantics.
- Native C2PA smoke testing remains environment-dependent.
- PixelSeal remains a challenger engine pending a real checkpoint benchmark.
- Camera capture, perspective distortion, AI editing/regeneration, and anti-distillation remain future test areas.
