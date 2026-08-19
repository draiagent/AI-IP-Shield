# Step 5.7 — C2PA + Provenance Layer

## 結論

**Provenance Core Gate:** `PASS`  
**C2PA Adapter Contract:** `PASS`  
**Native C2PA Runtime Smoke Test:** `PENDING / runtime unavailable in current sandbox`

本階段把 Step 5.6.3 已通過 Gate 的 `blind-native` 浮水印層，補上「來源證明 / 簽章 / 修改偵測」能力。

AI-IP Shield 現在有兩條互補證據鏈：

```text
Invisible Watermark / Fingerprint
        ↓
來源追蹤、外流副本辨識

Cryptographic Provenance
        ↓
簽章、完整性、信任關係、修改偵測
```

## 1. 新增 Provenance Core

新增 `aipshield/provenance.py`：

- Ed25519 signing key generation
- local trust store
- canonical JSON provenance manifest
- signed sidecar envelope
- SHA-256 asset binding
- trust / signature / asset-hash 分離驗證
- C2PA manifest builder
- C2PA signer / reader adapter
- `cawg.training-mining` policy assertion

## 2. Evidence 狀態

Sidecar 驗證不再只有 True / False：

- `VALID_TRUSTED`
- `VALID_UNTRUSTED`
- `MODIFIED`
- `INVALID_SIGNATURE`
- `INVALID`
- `MISSING`

其中：

> `MISSING` 不等於 Fake。

一份檔案可能因 Screenshot、重新輸出或平台處理失去 Provenance，但 Robust Watermark 仍可提供來源關聯證據。

## 3. Trust Model

「簽章正確」與「簽署者可信」是兩件不同的事。

```text
Signature Valid
    ↓
Public Key 可驗證簽章
    ↓
Trust Store
    ↓
是否信任這個 Signer
```

因此任意第三方自行建立簽章，不會被 AI-IP Shield 自動提升成 `CRYPTOGRAPHICALLY_VERIFIED`。

只有：

- watermark / registry match
- exact protected hash match
- provenance signature valid
- signer key in local trust store

同時成立時，才輸出：

`CRYPTOGRAPHICALLY_VERIFIED`

## 4. Privacy Fix

初版 Sidecar Manifest 曾直接攜帶 per-copy `fingerprint_id`。

這會把原本應留在 Registry / Invisible Watermark 的追蹤 ID 暴露在可見 Metadata 中。

已立即修正：

- Sidecar 不再輸出 raw `fingerprint_id`
- 改為 `fingerprint_commitment = SHA-256(fingerprint_id)`
- 真實 Copy / Recipient mapping 仍留在 Registry

## 5. Do Not Train

Sidecar Provenance 可記錄：

```text
ai_inference: notAllowed
ai_generative_training: notAllowed
```

C2PA manifest builder 對應使用：

`cawg.training-mining`

這是 provenance / policy evidence，不是技術上的強制防訓練機制。

## 6. C2PA Runtime

### ValidationState trust semantics 修正

本階段在對照官方 Reader JSON 定義時發現一個高風險語意問題，已立即修正：

- `Trusted` → `VALID_TRUSTED`：Manifest 有效，而且 active signature 受目前 verifier trust policy 信任。
- `Valid` → `VALID_UNTRUSTED`：Manifest 驗證無錯誤，但 active signature **未受信任**。
- `Invalid` → `INVALID`：存在驗證錯誤；除非 detailed status 明確指出 signature failure，否則不武斷標記為「簽章一定無效」。

舊版 contract 曾把 `Valid` 誤升級為 trusted；此錯誤已加入 regression tests，避免未來回歸。

`c2pa-python` adapter 已依目前官方 API 實作：

- `C2paSignerInfo`
- `Signer.from_info`
- `Builder.sign_file`
- `Reader`
- `get_validation_state`
- `get_validation_results`
- `get_active_manifest`

並加入 current-contract mock integration test。

但目前 sandbox 無法透過 pip 取得 `c2pa-python` native runtime，因此本階段不偽造 native C2PA signing 成績。

若 runtime 存在，可執行：

```bash
pip install 'ai-ip-shield[provenance]'

aipshield protect input.png protected.png \
  --provenance c2pa \
  --signing-key private_key.pem \
  --c2pa-cert certificate_chain.pem
```

## 7. Sidecar Provenance CLI

### Keygen

```bash
aipshield provenance-keygen \
  --private-key signing.pem \
  --public-key signing.pub.pem
```

### Trust

```bash
aipshield provenance-trust signing.pub.pem \
  --trust-store trust-store.json \
  --label "Enterprise Signer"
```

### Protect

```bash
aipshield protect input.png protected.png \
  --provenance sidecar \
  --signing-key signing.pem \
  --public-key signing.pub.pem \
  --do-not-train
```

### Verify

```bash
aipshield verify protected.png \
  --trust-store trust-store.json
```

## 8. Step 5.7 Gate

Gate Script：

```bash
python scripts/run_step57_provenance_gate.py
```

驗收項目：

- key generation
- trusted signer verification
- Do Not Train policy
- raw fingerprint privacy
- missing provenance semantics
- modified asset detection
- signed manifest tamper detection
- C2PA actions contract
- C2PA training-mining contract

結果：**9 / 9 PASS**

Automated tests：**23 / 23 PASS**

## 9. Security Boundary

Sidecar Provenance 提供本地 cryptographic evidence，但不是 C2PA Content Credential。

因此 UI / Report 必須分清楚：

- `aip-sidecar-ed25519`
- `c2pa`

不得把 Sidecar 包裝成 C2PA。

Production 簽署金鑰也不應長期以未加密 PEM 明文保存在一般檔案系統；正式企業版應串接 HSM / KMS / secure signing service。

## 10. Step 5.7 Decision

```text
Step 5.6.3
Robust Watermark Gate ✅
        ↓
Step 5.7
Fingerprint + Provenance + Trust + Evidence Fusion ✅
        │
        ├─ Local Ed25519 Provenance ✅
        ├─ Do Not Train Assertion ✅
        ├─ Trust Store ✅
        ├─ Tamper Detection ✅
        ├─ C2PA Adapter Contract ✅
        └─ Native C2PA Runtime Smoke ⏳
```

下一個產品層工作可以進入 PDF Adapter；真正 C2PA native smoke test 應在有 `c2pa-python` runtime 的 CI / Linux Python 3.10–3.12 環境補跑，且不得用 Sidecar 成績取代。
