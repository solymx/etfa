# 新增 ETF 操作指南

擴充流程分兩種情境。

## 情境 A：已支援投信的新 ETF（5 分鐘）

例如野村投信旗下多一檔新 ETF，只要在 `etfs.yaml` 加配置。

```yaml
  - code: "00XXXA"
    name: "新野村 ETF"
    issuer: "野村投信"
    category: "taiwan_stock"
    fetcher: "nomura"          # 沿用現有 fetcher
    params:
      fund_id: "00XXXA"
    enabled: true
```

存檔後直接 `python main.py --only 00XXXA` 驗證。

## 情境 B：新投信（30 分鐘 – 2 小時）

### Step 1：找到資料來源

投信公開持股的常見管道：
- **官網 API**：打開官網 ETF 持股頁，F12 開 DevTools → Network → XHR 看有沒有 JSON
- **基富通（ezmoney.com.tw）**：很多中小投信會走這個平台
- **官網 Excel 下載**：通常每天會產生 Excel 檔案
- **投信投顧公會**：`sitca.org.tw` 是最後手段

### Step 2：寫 fetcher

在 `core/fetchers/` 新增一個檔案，例如 `cathay.py`：

```python
"""國泰投信 fetcher。"""

from __future__ import annotations

import pandas as pd
import requests

from ..models import validate_holdings_df


def fetch(fund_code: str, **_) -> pd.DataFrame:
    """抓取國泰 ETF 持股。

    回傳的 DataFrame 必須有以下欄位：
        股票代號 (str), 股票名稱 (str), 股數 (float), 權重 (float)

    validate_holdings_df 會替你做型態轉換與空值檢查，
    你只要把來源資料湊成那四個欄位名。
    """
    source = f"cathay/{fund_code}"

    # 1) 呼叫來源 API / 爬網頁
    resp = requests.get(...)
    resp.raise_for_status()
    data = resp.json()

    # 2) 湊成統一格式的 DataFrame
    df = pd.DataFrame(data["holdings"])
    df = df.rename(columns={
        "stockCode": "股票代號",
        "stockName": "股票名稱",
        "shares": "股數",
        "weightPct": "權重",
    })[["股票代號", "股票名稱", "股數", "權重"]]

    # 3) 一定要呼叫 validate_holdings_df 做型態檢查
    return validate_holdings_df(df, source=source)
```

### Step 3：註冊 fetcher

編輯 `core/fetchers/__init__.py`，在 `REGISTRY` 加一行：

```python
from . import cathay

REGISTRY = {
    ...
    "cathay": cathay.fetch,
}
```

### Step 4：在 etfs.yaml 把對應 ETF 的 enabled 改 true

```yaml
  - code: "00400A"
    name: "國泰台股動能高息"
    issuer: "國泰投信"
    category: "taiwan_stock"
    fetcher: "cathay"
    params:
      fund_code: "XXX"
    enabled: true  # 從 false 改成 true
```

### Step 5：本地測試

```bash
python main.py --only 00400A
```

確認 `data/00400A.csv` 有正確產出，`reports/00400A.html` 內容合理。

## 📋 fetcher 撰寫檢查清單

- [ ] 函式簽名：`def fetch(**params) -> pd.DataFrame`
- [ ] 使用 `**_` 吸收不認識的參數（main.py 會傳 `search_date` 給所有 fetcher，不是每個都用得到）
- [ ] 回傳的 DataFrame 有 `股票代號`、`股票名稱`、`股數`、`權重` 四個欄位
- [ ] 最後呼叫 `validate_holdings_df(df, source=...)`
- [ ] 異常情況（找不到資料、API 掛掉）用 `raise ValueError(...)` 明確拋錯
- [ ] 請求加 timeout（建議 30 秒）
- [ ] 不要 hard-code 日期，收 `search_date` 或 `date_str` 參數

## 🧪 除錯技巧

如果 fetcher 抓到資料但格式有問題：

```bash
python -c "
from core.fetchers import get_fetcher
df = get_fetcher('nomura')(fund_id='00980A')
print(df.head())
print(df.dtypes)
"
```

如果想測試新舊比對邏輯：

```bash
# 先跑一次產生 data/00980A.csv
python main.py --only 00980A

# 等隔天再跑一次，觀察 reports/00980A.html 的「狀態」欄
python main.py --only 00980A
```
