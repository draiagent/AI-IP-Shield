# Step 5.6.3 — Production Engine Final Gate

## 結論

**Decision:** `GO_V0.1_CPU_PRODUCTION`  
**Pinned engine:** `blind-native` → `blind-watermark-native-adaptive`

本階段依 Step 4 的既定驗收門檻，完成 **100 張 Golden Test Set + 500 張 Negative Controls** 的正式 Gate。所有 V0.1 Gate 通過。

> 此結論代表「通過目前定義的 V0.1 攻擊模型與測試集」，不是宣稱浮水印不可破解，也不是第三方安全認證。

## 正式驗收結果

| Attack / Gate | Detection | Recovery | 最低門檻 | 結果 |
|---|---:|---:|---:|---|
| Original | 100% | 100% | 100% / 99% | PASS |
| Copy | 100% | 100% | 100% / 100% | PASS |
| Screenshot | 97% | 97% | 90% / 85% | PASS |
| Resize 75% | 98% | 98% | 95% / 95% | PASS |
| Resize 50% | 98% | 98% | 95% / 95% | PASS |
| Crop 10% | 99% | 99% | 90% / 90% | PASS |
| Crop 20% | 95% | 95% | 90% / 90% | PASS |
| Rotate 3° | 97% | 97% | 85% / 85% | PASS |
| JPEG 95 | 100% | 100% | 95% / 95% | PASS |
| JPEG 75 | 99% | 99% | 95% / 95% | PASS |
| JPEG 60 | 98% | 98% | 90% / 90% | PASS |
| Format Conversion | 99% | 99% | 85% / 80% | PASS |
| Resize75 + JPEG60 | 96% | 96% | 70% / 70% | PASS |
| Crop10 + JPEG75 | 96% | 96% | 70% / 70% | PASS |

### 其他 Gate

- False Positive Rate：**0 / 500 = 0.000%** → PASS
- Fingerprint collision test：**100,000 IDs，0 duplicate** → PASS
- 平均 PSNR：**38.00 dB**
- 平均 SSIM：**0.9545**
- Automated tests：**13 / 13 PASS**

## 本階段發現並立即修正的問題

### 1. 幾何同步失效

舊版遇到 Screenshot / Crop / Rotation 時，DWT/DCT block 相位會錯位。

修正：

- canonical geometry normalization
- screenshot inverse geometry
- symmetric crop recovery
- ±3° rotation recovery
- cyclic payload phase search

### 2. Crop 20% 的 1-pixel rounding 問題

實際圖片測試發現，單純使用 `round(observed / 0.8)` 可能把原始畫布尺寸算錯 1 pixel，足以讓 DWT block phase 失效。

修正：

- 依 symmetric crop 的 parity 條件反推可能原尺寸
- 搜尋最接近的 parity-valid canvas
- 再進行 ECC + CRC 驗證

修正後，實際測試圖片在 Crop 20% 可正確 Recover Fingerprint。

### 3. Phase search 效能瓶頸

舊版會對所有 cyclic phase 重複執行 convolutional/Viterbi decode。

修正：

- 建立 token-independent `MAGIC + VERSION` encoded marker
- 向量化所有 cyclic phase 比對
- 只對最佳候選執行 ECC/CRC decode

結果：Negative-control 驗證速度大幅改善，同時保留 CRC 作最終判斷。

### 4. Production engine alias 可能漂移

`blind` adapter 在不同環境可能自動切換成 upstream package，會造成「測試的是 A、部署卻跑 B」的風險。

修正：

- V0.1 production engine 明確 pin 為 `blind-native`
- CLI / Protect / Verify / Attack Lab 預設值全部改為 `blind-native`
- `dct-qim` 保留為 benchmark only

### 5. 大型一次性 Benchmark 容易超時

修正：

- 新增 resumable chunk runner
- Attack / Negative Control 可分段執行
- Finalize 前強制檢查 100 / 500 dataset completeness

## 實際圖片 Regression

使用專案對話中的實際資訊圖卡再次執行 T01–T05 與 Composite Attack：

- **14 / 14（含 Original）全部成功 Recover**
- Crop 20%：修正後成功
- PSNR：**37.38 dB**
- SSIM：**0.9862**

完整資料：`reports/step5.6.3/REAL-IMAGE-REGRESSION.json`

## 殘餘風險

100 張 Golden Set 中，少數失敗案例集中在資訊密度高的 infographic variants。Aggregate Gate 已達標，但 V0.2 應繼續針對：

- dense infographic
- 更高比例 crop
- 更大角度 rotation
- 真實手機拍屏 / perspective distortion
- AI Editing / AI Regeneration

進行紅隊強化。

## PixelSeal 狀態

PixelSeal adapter / runtime integration 已完成，但本執行環境沒有可用的 `videoseal` runtime 與官方 PixelSeal checkpoint，因此：

- 不產生 surrogate PixelSeal 分數
- 不把官方 benchmark 當成 AI-IP Shield 實測成績
- PixelSeal 保留為後續 GPU challenger engine

V0.1 因 `blind-native` 已通過全部 Step 4 Gate，因此可繼續 Step 5.7 C2PA / Provenance。
