# FAL.ai Integration Setup (2026-06-22)

## 現況
- `fal-client` SDK v1.0.0 已成功安裝至 hermes-agent venv
- `~/.hermes/.env` 中 `FAL_AI_API_KEY`（錯誤命名）被註釋，key 未啟用
- `~/.hermes/skills/minimax-multimodal-toolkit/references/fal-ai-flux.md` 存在但假設 key 已就緒

## 核心發現：FAL_KEY vs FAL_AI_API_KEY

**問題**: fal-client SDK 讀取的環境變數是 `FAL_KEY`，但 hermes .env 範本註釋的是 `FAL_AI_API_KEY`。兩者不一致導致 SDK 永遠抓不到 key。

**驗證**:
```python
# hermes-agent venv 內測試
/home/hoonsoropenclaw/.hermes/hermes-agent/venv/bin/python3 -c "
import fal_client, os
print('FAL_KEY present:', bool(os.environ.get('FAL_KEY')))
print('FAL_AI_API_KEY present:', bool(os.environ.get('FAL_AI_API_KEY')))
# SDK 實際讀取 FAL_KEY
"
# 輸出：FAL_KEY present: False, FAL_AI_API_KEY present: False
```

**正確 env 格式**:
```
FAL_KEY=fla_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 安裝路徑
```bash
uv pip install fal-client --python /home/hoonsoropenclaw/.hermes/hermes-agent/venv/bin/python3
# Installs: fal-client==1.0.0, aiofiles, asyncstdlib, msgpack
```

## FLUX.1-dev 定價（2026）
- `fal-ai/flux/dev`: $0.025/image
- `fal-ai/flux-pro/v1.1`: $0.05/image
- `fal-ai/flux-schnell`: $0.003/image

## image-01 失敗時的 FLUX 替換觸發條件
當 prompt 含以下任意組合時，直接告知用戶 FLUX 報價並詢問是否切換：
1. body-shape adjective (curvy/hourglass/voluptuous/busty)
2. bird's-eye + abstract style (line art/flat colors)
3. explicit content（image-01 會過度過濾）

## 待辨事項
1. 用戶需在 fal.ai 註冊並取得 `FAL_KEY`
2. 在 `~/.hermes/.env` 加入 `FAL_KEY=fla_xxx`
3. 驗證：`/home/hoonsoropenclaw/.hermes/hermes-agent/venv/bin/python3 -c "import fal_client; print(fal_client.subscribe('fal-ai/flux/dev', arguments={'prompt':'a cat','image_size':'square'}, with_logs=False)['images'][0]['url'])"`
