# 🗂️ 8 家投信調查清單

這是 Phase 2 要擴充的 8 家投信，每家附上**建議起始頁面**與**小提示**。
依此順序調查（最簡單的排最前）。

---

## ✅ 進度追蹤

| 順序 | 投信 | ETF | 狀態 | 調查頁面 |
|---|---|---|---|---|
| 1 | 第一金 | 00994A | ⏸️ 暫緩（詳見下方） | https://www.fsitc.com.tw/FundDetail.aspx?ID=182 |
| 2 | 台新 | 00986A, 00987A | ✅ 已啟用 | https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/00987A |
| 3 | 兆豐 | 00996A | ⬜ 待調查 | https://www.megafunds.com.tw/ |
| 4 | 中信 | 00983A, 00995A | ⬜ 待調查 | https://www.ctbcinvestments.com/ |
| 5 | 元大 | 00990A | ⬜ 待調查 | https://www.yuantaetfs.com/ |
| 6 | 安聯 | 00984A, 00993A | ⏸️ 暫緩（CSRF 保護難繞） | https://etf.allianzgi.com.tw/etf-info/E0002 |
| 7 | 摩根 | 00401A, 00989A | ⬜ 待調查 | https://www.jpmrich.com.tw/ |
| 8 | 國泰 | 00400A | ✅ 已啟用 | https://www.cathaysite.com.tw/ETF/detail/EEA |

## ⏸️ 關於第一金 00994A 的暫緩

2026-04-19 調查後發現頁面有兩種持股揭露：
- **前十大靜態表**：只有 10 檔、缺股票代號與股數、資料是月底快照，不適合本系統
- **每日完整揭露**：要點「資料日期 → 查詢」觸發 AJAX，但當時未抓 AJAX 請求

若未來想啟用，需要：
1. 打開 https://www.fsitc.com.tw/FundDetail.aspx?ID=182
2. F12 → Network → 下拉選日期 → 點查詢 → 抓 AJAX 請求
3. 把 cURL 貼給 Claude，骨架檔案 `core/fetchers/firstsino.py` 已預留 TODO 區塊

## ⏸️ 關於安聯 00984A/00993A 的暫緩

2026-04-19 調查：API 確實存在
```
POST https://etf.allianzgi.com.tw/webapi/api/Fund/GetFundAssets
Body: {"FundID":"E0001"}  # 00984A
     {"FundID":"E0002"}  # 00993A
```
但有 ASP.NET Core Antiforgery 保護，實測三種策略（直接 POST、GET 頁面 → POST、
GET 根目錄 + GET 頁面 → POST）全部失敗。前端 JS 可能在內部某 API 握手時才拿到
token，要繞過需要 Selenium/Playwright 或逆向 JS。

**未來恢復選項**：
- 用 Selenium/Playwright 跑真瀏覽器拿 cookie
- 手動從瀏覽器複製 cookie 設環境變數（無法自動化）
- 看 ezmoney 基富通是否上架安聯 ETF（可複用 ezmoney fetcher）

詳見 `core/fetchers/allianz.py` 頂端註解。

**進度標示**：⬜ 待調查 · 🔍 抓 API 中 · 💬 已貼給 Claude · ✅ fetcher 寫完 · 🎉 本機測試通過

---

## 1️⃣ 第一金投信（00994A）

**起始頁面**：https://www.fsitc.com.tw/etf/etf-info/FS994A

**調查流程**：
1. 開啟上方頁面
2. F12 → Network → Fetch/XHR
3. 找「基金持股」或「持股明細」tab，點進去
4. 搜尋 response 中的 `2330`

**小提示**：
- 第一金官網傳統上是 `.NET` 框架，API 可能長得像 `/WebService/xxx.asmx/GetHoldings` 這種
- 如果看到 `.asmx` 或 `.ashx` 端點，那就是了

---

## 2️⃣ 台新投信（00986A, 00987A）

**起始頁面**：https://www.taishinfunds.com.tw/

**調查流程**：
1. 首頁搜尋 「00987A」或「台新臺灣優勢成長」
2. 進入基金詳細頁，找「持股」相關 tab
3. F12 → Network → 搜尋 `2330`

**小提示**：
- 兩檔 ETF（00986A 全球龍頭、00987A 臺灣優勢）很可能走同一支 API
- 同一家投信 → 很大機率只需要抓一次

---

## 3️⃣ 兆豐投信（00996A）

**起始頁面**：https://www.megafunds.com.tw/

**小提示**：
- 00996A 是兆豐的第一檔主動式 ETF，API 可能獨立
- 如果找不到，搜尋 `兆豐台灣豐收 持股`

---

## 4️⃣ 中信投信（00983A, 00995A）

**起始頁面**：https://www.ctbcinvestments.com/

**小提示**：
- 00983A 是海外股（ARK 創新），00995A 是台股。持股明細格式可能稍有不同
- 但 API endpoint 應該相同，只是 ETF 代號參數不同

---

## 5️⃣ 元大投信（00990A）

**起始頁面**：https://www.yuantaetfs.com/

**小提示**：
- 元大是 ETF 老牌發行商，網站有獨立 ETF 專區 `yuantaetfs.com`
- 很可能有公開 API（因為發行很多 ETF）

---

## 6️⃣ 安聯投信（00984A, 00993A）

**起始頁面**：https://tw.allianzgi.com/

**小提示**：
- 德商背景，網站可能走國際化框架
- 如果找不到 API，可能資料在 ezmoney 基富通平台（現成 fetcher 可用）

---

## 7️⃣ 摩根投信（00401A, 00989A）

**起始頁面**：https://www.jpmrich.com.tw/

**小提示**：
- 摩根的基金持股**可能要登入會員**才能看完整明細（如果是這樣告訴我，改抓公開的前十大）
- 或試試基富通 ezmoney 平台

---

## 8️⃣ 國泰投信（00400A）

**起始頁面**：https://www.cathaysite.com.tw/ETF/detail/EEA

**小提示**：
- 國泰 ETF 專區是 `cathaysite.com.tw`，主站是 `cathayholdings.com`
- 看到「持股權重」tab 點進去，那個動作會觸發 XHR
- 國泰發了超過 30 檔 ETF，找到 API 後 **很多被動式 ETF 也能順便支援**（Phase 3 番外篇？）

---

## 🔄 給 Claude 的報告範本

您抓到 API 後，用這個格式貼給我：

```markdown
## 調查結果：XXX 投信

**狀態**：✅ 成功 / ❌ 失敗

**Request 資訊**：
```

（接著貼 cURL 或手動整理的四大項，詳見 FIND_API_SOP.md）

---

## ⏸️ 如果某家卡住

沒關係，跳過繼續下一家。所有 8 家都不需要一次完成，**有一家就加一家**。每加一家投信，`etfs.yaml` 就多幾檔 ETF 可以追蹤，系統仍持續可用。
