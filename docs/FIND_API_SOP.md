# 🔍 投信持股 API 調查 SOP

本指南教您用瀏覽器 DevTools 找出任一投信的「持股資料 API」，時間約 **2-5 分鐘 / 每家**。

---

## 📋 準備工作

**需要的工具**：
- 任一現代瀏覽器（Chrome / Edge / Firefox）
- 該投信官網的 ETF 持股頁面 URL（已在每個 fetcher 骨架的註解中提供）

---

## 🔎 通用 5 步驟

### 步驟 1：開啟 DevTools

打開投信的 ETF 持股頁面，按 **F12** （或 Mac 用 `Cmd+Option+I`）。

### 步驟 2：切到 Network 分頁 + 篩選

1. 點上方 tab 的 **Network**（網路）
2. 點 **Fetch/XHR** 篩選器（排除圖片、CSS 等雜訊）
3. 勾 **Preserve log**（保留記錄，避免頁面導航時清掉）

![Devtools-layout](https://imgur.com/example.png) <!-- 這行不會影響檔案 -->

### 步驟 3：觸發持股資料載入

- **最簡單**：按 **Ctrl+R / Cmd+R** 重新整理頁面
- 有些網站需要點「持股權重」tab 才會呼叫 API

### 步驟 4：找出持股 API

Network 面板會列出幾十個請求。用以下技巧鎖定：

**🔥 最快方法：用關鍵字搜尋 response**

1. 在 Network 面板右上角找 🔍 搜尋按鈕
2. 搜尋 `2330` 或 `台積電`（絕大多數主動式 ETF 都持有）
3. 找到的請求 99% 就是持股 API

**💡 備援方法：看請求大小**
- 持股 API 的 response 通常 > 10 KB（有 30-60 檔股票）
- 按 Size 欄位排序找大的

### 步驟 5：匯出 API 資訊

找到持股 API 後，**右鍵 → Copy → Copy as cURL**（或 `Copy as fetch`），把內容貼給 Claude。

**或者**，手動複製以下 4 項給 Claude：

1. **Request URL**（完整網址）
2. **Request Method**（GET / POST）
3. **Request Headers**（重要的：`Content-Type`、`Referer`、`Origin`）
4. **Request Payload**（如果是 POST，body 的內容）
5. **Response 的前幾行 JSON**（看欄位結構）

---

## 📝 貼給 Claude 的範本

```
📌 投信：XXX（例：國泰投信）
📌 ETF 代號：00400A

Request URL: https://api.xxx.com.tw/fund/holdings?fundCode=XXX
Request Method: POST

Request Headers:
  Content-Type: application/json
  Referer: https://www.xxx.com.tw/

Request Payload (body):
{
  "fundCode": "ABC",
  "date": "2026-04-17"
}

Response (節選前兩筆):
{
  "code": 0,
  "data": {
    "holdings": [
      {
        "stockCode": "2330",
        "stockName": "台積電",
        "shares": 1200000,
        "weight": 28.5
      },
      ...
    ]
  }
}
```

---

## 💡 Tips

- **如果找不到 API**：可能是 server-side render（資料直接寫在 HTML 裡）或 WebSocket。告訴我頁面 URL，我幫您改用爬蟲方式。
- **如果 API 要 token**：抓 Request Headers 中的 `Authorization` 或 Cookie，一起貼給我。
- **如果多個 ETF 用同一支 API**：只要調查 1 次，告訴我每檔 ETF 對應的 `fundCode` 就行。
- **同一家投信的 API 通常統一**：例如國泰的 00400A 和 00878 走同一支 API，只是 `fundCode` 不同。

---

## ⏱️ 預估時間

| 家數 | 時間 |
|---|---|
| 1 家 | 2-5 分鐘 |
| 8 家 | 20-40 分鐘 |

不趕時間的話，可以一天調查 1-2 家，慢慢加。

---

## 🆘 遇到問題？

把 DevTools 的截圖給我，說明您卡在哪一步，我會協助。
