# monitor_etf_tw

追蹤台灣主動式 ETF 每日持股變動。

## ✨ 功能

- 📊 **每日持股快照**：自動抓取並比對前一日，標記新進 / 加碼 / 減碼 / 清倉
- 📈 **歷史趨勢分析**：累積快照後產出互動式趨勢圖
- 🎯 **跨 ETF 曝險強度**：彙總所有 ETF 對同一檔個股的合計權重
- 🌐 **首頁導航**：`reports/index.html` 一頁看完所有 ETF 狀態
- 📋 **股票專屬頁**：每支被持有的股票都有 `reports/stocks/<代號>.html`，看哪些 ETF 在買
- 🌟 **個人關心清單**：在 `etfs.yaml` 設 watchlist，首頁會特別顯示這些股票的異動
- ⏪ **時間智慧**：可隨意指定任何日期執行，系統自動處理補歷史邏輯不混淆

## 📁 專案架構

```
monitor_etf_tw/
├── etfs.yaml                 ← 所有 ETF 配置（新增 ETF 從這改）
├── main.py                   ← 主入口
├── requirements.txt
├── core/
│   ├── models.py             ← 統一資料格式與驗證
│   ├── comparator.py         ← 新舊持股比對
│   ├── storage.py            ← CSV 存檔與備份
│   ├── reporter.py           ← HTML 日報 + 首頁
│   ├── analyzer.py           ← 歷史趨勢分析器
│   ├── exposure.py           ← 跨 ETF 曝險彙總
│   └── fetchers/             ← 各投信資料抓取器
│       ├── nomura.py         ← 野村（00980A / 00985A / 00999A）
│       ├── ezmoney.py        ← 統一（00981A 等）
│       ├── capital.py        ← 群益（00982A / 00992A / 00997A）
│       └── fhtrust.py        ← 復華（00991A / 00998A）
├── data/
│   ├── <CODE>.csv            ← 最新快照（下次比對基準）
│   └── <CODE>_backup/
│       └── YYYY-MM-DD.csv    ← 歷史快照
├── reports/
│   ├── index.html            ← 首頁
│   ├── exposure.html         ← 跨 ETF 曝險
│   ├── <CODE>.html           ← 單檔日報
│   └── <CODE>_trend.html     ← 單檔趨勢
└── .github/workflows/
    └── daily_monitor.yml     ← 每日自動執行
```

## 🚀 使用方式

### 本地執行

```bash
pip install -r requirements.txt

# 跑全部啟用中的 ETF
python main.py

# 只跑單一檔
python main.py --only 00980A

# 只跑某家投信
python main.py --issuer 野村投信

# 指定歷史日期（補資料用）
python main.py --date 2026-04-15
```

### 🔐 遇到 SSL 憑證錯誤？

部分投信（例如野村）的 SSL 憑證缺少 `Subject Key Identifier` 欄位，
在較嚴格的環境（Python 3.13、Kali Linux）會驗證失敗，錯誤訊息類似：

```
SSLError: certificate verify failed: Missing Subject Key Identifier
```

本專案的 `core/http.py` 已內建三層 fallback：
1. 正常 SSL 驗證
2. 改用 `certifi` 的 CA bundle 重試
3. 若設 `MONITOR_ETF_ALLOW_INSECURE=1` 環境變數，關閉驗證

如果前兩層都失敗，可以臨時繞過（僅限在您信任的網路下）：

```bash
export MONITOR_ETF_ALLOW_INSECURE=1
python main.py --only 00980A
```

GitHub Actions 的 Ubuntu runner 通常不會遇到這個問題，所以 CI 端保持預設安全模式即可。


### 新增 ETF

見 [`docs/ADD_NEW_ETF.md`](docs/ADD_NEW_ETF.md)。簡言之兩步：

1. 如果是**已支援投信**（野村、統一、群益、復華），只要在 `etfs.yaml` 加一段配置
2. 如果是**新投信**，在 `core/fetchers/` 下新增一個模組，再註冊到 `fetchers/__init__.py`

## 🏗️ 資料流

```
etfs.yaml 配置
    ↓
main.py 讀取配置
    ↓
對每檔 ETF 執行：
    fetcher 抓原始資料 → validate_holdings_df（統一欄位）
                        ↓
                     comparator.compare（與舊快照比對）
                        ↓
                     storage.save_snapshot（存新檔 + 備份）
                        ↓
                     reporter.generate_daily_report（產 HTML 日報）
                        ↓
                     analyzer.analyze（產歷史趨勢頁）
    ↓
reporter.generate_index（彙總首頁）
    ↓
exposure.aggregate_exposure（跨 ETF 曝險）
```

## 🔌 已支援的投信與 API 來源

| 投信 | ETF | 資料來源 | 格式 |
|---|---|---|---|
| 野村 | 00980A, 00985A, 00999A | `nomurafunds.com.tw` API | JSON |
| 統一 | 00981A | `ezmoney.com.tw` 爬蟲 | HTML (embedded JSON) |
| 群益 | 00982A | `capitalfund.com.tw` API | JSON |
| 復華 | 00991A | `fhtrust.com.tw` | Excel |
| 國泰 | 00400A | `cwapi.cathaysite.com.tw` API | JSON |
| 台新 | 00986A, 00987A | `tsit.com.tw` 爬蟲 | HTML |

Phase 2 待加：摩根、中信、元大、兆豐、第一金、安聯。

## 📝 長期異動日誌（track_changelog）

想長期觀察某檔 ETF 經理人的操作風格？在 `etfs.yaml` 該 ETF 加一行
`track_changelog: true`：

```yaml
  - code: "00981A"
    name: "統一台股增長"
    # ...其他設定...
    enabled: true
    track_changelog: true  # 啟用異動日誌
```

每次跑完會把當日異動（只記錄**新進/加碼/減碼/清倉**，不記錄持平）
追加到 `data/00981A_changelog.csv`。長期累積後可做分析：

```python
import pandas as pd
log = pd.read_csv("data/00981A_changelog.csv")

# 哪些股票最常被加碼？
log[log["狀態"] == "加碼"]["股票名稱"].value_counts().head(10)

# 某支股票的買賣歷史
log[log["股票名稱"] == "台積電"].sort_values("日期")

# 每月換股頻率
log["月份"] = log["日期"].str[:7]
log.groupby(["月份", "狀態"]).size().unstack()
```

檔案格式：
```csv
日期,股票代號,股票名稱,狀態,股數變化,今日股數,今日權重
2026-04-16,2330,台積電,加碼,10000,110000,13.0
2026-04-16,6488,環球晶,新進,8000,8000,2.1
2026-04-17,2317,鴻海,清倉,-30000,0,0
```

## 📝 歷史沿革

此專案原本為每檔 ETF 維護一個獨立 .py 檔案。隨著 ETF 數量增加，
重構為配置驅動（config-driven）+ 共用核心模組架構。原本的 980a.py /
981a.py 等檔案已被 `core/fetchers/` 下的模組取代。

## 🚧 Phase 2：擴充 8 家新投信

為了覆蓋全部 23 檔台股主動式 ETF，需要為以下 8 家投信各寫一個 fetcher：
國泰、摩根、中信、安聯、台新、元大、第一金、兆豐。

每家的 fetcher 骨架已在 `core/fetchers/` 準備好，只差 API 端點資訊。
**工作流程**：

1. **您**：參考 [`docs/FIND_API_SOP.md`](docs/FIND_API_SOP.md) 開 DevTools 抓某家投信的 API（2-5 分鐘）
2. **您**：把抓到的 Request URL / Headers / Payload / Response 貼給 Claude
3. **Claude**：把資訊填進對應的 fetcher 骨架（如 `core/fetchers/cathay.py`）
4. **您**：用 `python scripts/test_fetcher.py <name> --params ...` 單獨測試
5. **您**：測試通過後把 `etfs.yaml` 對應 ETF 的 `enabled` 改成 `true`

進度追蹤見 [`docs/PHASE2_INVESTIGATION.md`](docs/PHASE2_INVESTIGATION.md)。

## 📜 License

MIT
