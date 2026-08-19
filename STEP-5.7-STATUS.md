# Step 5.7 Status — C2PA + Provenance

## Decision

**`PASS_WITH_C2PA_RUNTIME_PENDING`**

Step 5.7 的本地 Cryptographic Provenance 核心已完成並通過；C2PA adapter / manifest contract 已通過，但目前 sandbox 未安裝原生 `c2pa-python` runtime，因此 Embedded Content Credential 的 native smoke test 保留為 Pending，不使用 surrogate 成績代替。

## Completed

- Ed25519 provenance keypair + local trust store
- Signed provenance sidecar
- SHA-256 asset binding
- `VALID_TRUSTED` / `VALID_UNTRUSTED` 分離
- Modified asset detection
- Signed-manifest tamper detection
- Missing provenance ≠ Fake
- Watermark + Registry + Provenance evidence fusion
- Privacy：sidecar 不暴露 raw per-copy fingerprint，僅保存 SHA-256 commitment
- Do Not Train policy signal
- C2PA `c2pa.actions` manifest contract
- C2PA `cawg.training-mining` contract
- Step 5.6 Registry schema migration

## Critical fix during Step 5.7

官方 C2PA ValidationState 定義中：

```text
Trusted = manifest valid + active signature trusted
Valid   = manifest valid + active signature NOT trusted
Invalid = validation errors exist
```

因此 AI-IP Shield 現在只會把 `Trusted` 映射成 `VALID_TRUSTED`；`Valid` 必須是 `VALID_UNTRUSTED`。這可避免把未受信任的自簽或未知 signer 錯升級為可信來源。

## Validation

- Automated tests: **23 / 23 PASS**
- Step 5.7 core gates: **9 / 9 PASS**
- Actual image demo: trusted / missing provenance / modified asset 三種路徑皆符合預期
- Native C2PA: **BLOCKED_NOT_INSTALLED**

## Security packaging

Demo private signing key is ephemeral and **excluded from the distributable ZIP**. Only public verification material and signed demo artifacts are retained.
