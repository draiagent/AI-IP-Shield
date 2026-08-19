# AI-IP-Shield

AI-IP Shield 是一套 AI 時代的智慧財產保護工具，整合隱形浮水印、Fingerprint 指紋追蹤、SHA-256 完整性驗證、數位簽章、來源證明與 Attack Lab，支援圖片與 PDF 的防偽、防盜、來源追蹤與證據驗證，並可整合 ChatGPT、Codex 與 Claude Code Skill 工作流程。

## 支援範圍（V0.1）

- JPG / JPEG / PNG 圖片
- PDF（點陣視覺保護模式，不保留可選取文字/超連結/表單/向量）
- 每份副本的隱形指紋 + SQLite 登記檔
- SHA-256 完整性驗證
- Ed25519 sidecar 數位簽章來源證明、本地信任庫
- 若環境支援，可選用 C2PA 標準
- 確定性 T01–T05 攻擊測試（Attack Lab）

V0.1 **不**支援：原生 PPTX 保護、結構保留式 PDF 保護、保證浮水印一定存活、防蒸餾偵測。

> 核心規則：不得宣稱「無法移除」「100% 防盜」「100% 防止 AI 訓練」或提供法律侵權證明，只回報技術證據與已知限制。

## 安裝

前往 [Releases](https://github.com/draiagent/AI-IP-Shield/releases) 下載最新版的 `.whl`，然後：

```bash
python -m pip install ai_ip_shield-0.1.0-py3-none-any.whl
aipshield doctor
```

`doctor` 會檢查核心依賴（numpy、opencv-python、Pillow、cryptography、PyMuPDF）與選用執行環境是否就緒，回傳 `"core_ready": true` 即代表基本保護/驗證功能可用。

### 選用功能（需要另外安裝）

核心保護/驗證功能不需要額外套件。以下功能需要對應的 extras：

| 功能 | 安裝指令 |
|---|---|
| C2PA 標準來源證明 | `pip install "ai-ip-shield[provenance]"` |
| 舊版 blind-watermark 引擎（V0.1 預設引擎是 `blind-native`，一般不需要） | `pip install "ai-ip-shield[blind]"` |
| Pixelseal 深度學習浮水印 | `pip install "ai-ip-shield[pixelseal]"` |

## 快速開始

```bash
# 1. 保護一張圖片
aipshield protect input.png protected.png --registry data/registry.sqlite3

# 2. 立即驗證
aipshield verify protected.png \
  --registry data/registry.sqlite3 \
  --report-json verify.json \
  --report-md verify.md

# 3. 需要時加上來源證明
aipshield provenance-keygen --private-key signing.pem --public-key signing.pub.pem
aipshield provenance-trust signing.pub.pem --trust-store trust-store.json --label publisher
```

PDF 用法相同，把 `.png` 換成 `.pdf` 即可。私鑰（`signing.pem`）絕對不要進版控。

## 安裝到 Claude Code / Codex / ChatGPT 的 Agent Skill

CLI 內建一鍵安裝指令：

```bash
# Claude Code（專案範圍，裝到 .claude/skills/ai-ip-shield/）
aipshield skill-install --host claude --scope project

# Claude Code（使用者範圍，全域可用）
aipshield skill-install --host claude --scope user

# Codex（裝到 .agents/skills/ai-ip-shield/）
aipshield skill-install --host codex --scope project

# 同時裝兩種
aipshield skill-install --host both --scope project
```

裝好之後，在 Claude Code / Codex 對話中用自然語言描述需求（例如「幫我保護這張圖片」「驗證這個檔案是不是原圖」）即可自動觸發 Skill。

ChatGPT 目前無法由 CLI 直接安裝，改用匯出後手動上傳：

```bash
aipshield skill-export --output ai-ip-shield-skill-v0.1.0.zip
```

再到 ChatGPT 的 Skills UI（若帳號/工作區已開放 Skill 上傳）上傳這個 ZIP。

## 從原始碼安裝（開發者）

```bash
python -m pip install -e .
aipshield doctor
python -m pytest -q
```

## Release 內容

每個版本的 [Releases](https://github.com/draiagent/AI-IP-Shield/releases) 頁面提供 4 個檔案：

| 檔案 | 用途 |
|---|---|
| `AI-IP-Shield-vX.Y.Z-release.zip` | 完整原始碼 + 文件（README、docs/、範例），適合直接部署使用 |
| `AI-IP-Shield-vX.Y.Z-source.tar.gz` | 同上內容，tar.gz 格式 |
| `ai_ip_shield-X.Y.Z-py3-none-any.whl` | 可直接 `pip install` 的 Python 套件 |
| `ai-ip-shield-skill-vX.Y.Z.zip` | 獨立的 Agent Skill 包（給已裝好 CLI 的使用者，或給 ChatGPT 上傳用） |

## 授權

見 [LICENSE](LICENSE)（隨完整原始碼包提供）。
