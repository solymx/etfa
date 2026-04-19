# 🚀 全新 GitHub Repo 部署教學（超詳細版）

照著每一步做就會成功。預計 **15-20 分鐘**。

---

## 📦 部署前準備

- ✅ 有一個 GitHub 帳號（您的是 `solymx`）
- ✅ 本機已安裝 git（Kali 預設就有）
- ✅ 已解壓 `monitor_etf_tw_refactored.zip` 到 `~/Desktop/et/`
- ✅ 已在本機測試過 8 個 fetcher 都能動

---

# 🎯 Part 1：在 GitHub 建立新 Repo

## Step 1.1 — 打開 GitHub 新 Repo 頁面

用瀏覽器打開：
```
https://github.com/new
```

如果沒登入會要求您登入，登入後自動進到建立頁面。

## Step 1.2 — 填寫 Repo 設定

會看到表單，照以下填：

| 欄位 | 填什麼 | 說明 |
|---|---|---|
| **Owner** | `solymx`（應該預設就是）| 您的 GitHub 帳號 |
| **Repository name** | `monitor_etf_tw_v2` | 建議這個名字，跟舊的區分 |
| **Description**（選填） | `台股主動式 ETF 每日持股監控 v2` | 說明 |
| **Public / Private** | ⭕ **Public**（推薦）| Public 才能用免費 GitHub Pages |
| **Initialize this repository with**： | | |
| `☐ Add a README file` | **不要勾** | 我們本機已有 README |
| `☐ Add .gitignore` | **不要勾** | 我們本機已有 |
| `☐ Choose a license` | **不要勾** | 之後要加再加 |

## Step 1.3 — 點 "Create repository"

按下綠色的 **Create repository** 按鈕。

建立成功後會看到一個頁面，上面有幾段快速指令。**認住這個網址**（就是您新 repo 的網址）：

```
https://github.com/solymx/monitor_etf_tw_v2
```

---

# 🎯 Part 2：本機推上 GitHub

## Step 2.1 — 打開終端機，進到專案目錄

```bash
cd ~/Desktop/et/monitor_etf_tw_refactored
```

## Step 2.2 — 確認檔案結構正確

```bash
ls
```

應該看到：
```
README.md  core  docs  etfs.yaml  main.py  requirements.txt
scripts
```

（`.github` 和 `.gitignore` 是隱藏檔，用 `ls -la` 才看得到）

## Step 2.3 — 初始化 git

```bash
git init
git branch -M main
```

會輸出：
```
Initialized empty Git repository in /root/Desktop/et/monitor_etf_tw_refactored/.git/
```

## Step 2.4 — 設定您的 Git 身份（第一次用才需要）

```bash
git config user.name "solymx"
git config user.email "您的email@example.com"
```

把 email 改成**您 GitHub 帳號登記的 email**。

## Step 2.5 — 連結到新 Repo

```bash
git remote add origin https://github.com/solymx/monitor_etf_tw_v2.git
```

## Step 2.6 — 第一次 commit

```bash
git add .
git commit -m "feat: initial commit - 8 active ETFs with daily monitoring"
```

會輸出：
```
[main (root-commit) xxxxxxx] feat: initial commit...
 35 files changed, 2800 insertions(+)
 create mode 100644 .github/workflows/daily_monitor.yml
 ...（會列出所有 commit 的檔案）
```

## Step 2.7 — 推上 GitHub

```bash
git push -u origin main
```

**會要求您輸入 GitHub 帳密！** 這是關鍵一步：

### ⚠️ 關於 GitHub 認證（2021 後的重點）

GitHub **不再允許用密碼推送**，要用 **Personal Access Token (PAT)**：

**情況 A：您之前有設過 PAT** → 帳密正常輸入
- Username: `solymx`
- Password: `您的 PAT`（不是您 GitHub 登入密碼！）

**情況 B：您沒 PAT，要先建一個**：

1. 瀏覽器打開 https://github.com/settings/tokens
2. 點 **Generate new token (classic)**
3. Note 填 `monitor_etf_tw_v2`
4. Expiration 選 **90 days** 或 **No expiration**
5. Scopes 只要勾 ✅ **repo**（整個區塊）
6. 捲到最底點 **Generate token**
7. **立刻複製** 那串 `ghp_xxxxx...`（離開頁面就看不到了！）
8. 回到終端機，密碼欄貼上這串 token

### Step 2.7 成功的話會看到：

```
Enumerating objects: 45, done.
Counting objects: 100% (45/45), done.
...
To https://github.com/solymx/monitor_etf_tw_v2.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

此時刷新您的 GitHub repo 頁面 → 檔案都上去了！

---

# 🎯 Part 3：設定 GitHub Actions 權限

**這步非常重要**，不做 workflow 會跑但無法 commit 回 repo。

## Step 3.1 — 打開 Repo 設定

在您 repo 頁面（`https://github.com/solymx/monitor_etf_tw_v2`）：

1. 點上方 **Settings** tab（齒輪圖示旁）
2. 左側選單捲到下面，點 **Actions** → **General**

## Step 3.2 — 設定 Workflow 權限

捲到頁面下半部 **Workflow permissions** 區塊，會看到兩個 radio button：

```
○ Read repository contents and packages permissions
○ Read and write permissions            ← 選這個！
```

1. 點選 **Read and write permissions**
2. 下方多出來的勾選框，勾選 ✅ **Allow GitHub Actions to create and approve pull requests**
3. 按 **Save**

---

# 🎯 Part 4：第一次手動觸發 Workflow

**關鍵**：今天是禮拜日，要用 `target_date=2026-04-17` 才能抓到有效資料。

## Step 4.1 — 去 Actions 頁面

在 repo 頁面：
1. 點上方 **Actions** tab
2. 如果出現 "I understand my workflows, go ahead and enable them" → 點它

## Step 4.2 — 手動觸發

在 Actions 頁面：

1. **左側** 選單會看到 `Daily ETF Monitor`（就是 workflow 的名字），點它
2. **右側上方** 會看到一個 `This workflow has a workflow_dispatch event trigger.` 的提示
3. 旁邊有灰色按鈕 **Run workflow**，點它
4. 會跳出下拉表單：

```
┌─────────────────────────────────────────┐
│ Use workflow from:  [Branch: main ▾]    │
│                                         │
│ 只跑指定 ETF 代號（留空則全跑）         │
│ [                          ]            │
│                                         │
│ 指定資料日期 YYYY-MM-DD（禮拜日建議填）│
│ [2026-04-17                ]  ← 填這個！│
│                                         │
│ [ Run workflow ]  ← 綠色按鈕            │
└─────────────────────────────────────────┘
```

5. **指定資料日期** 填 `2026-04-17`
6. 點綠色的 **Run workflow** 按鈕

## Step 4.3 — 等 Workflow 執行

頁面會自動刷新（或手動重整），會看到一個新的 run 出現：

```
🟡 Daily ETF Monitor                  Manual triggered by @solymx
   main   少於 1 分鐘前
```

點進去看進度，從 🟡 Queued → 🟡 In progress → ✅ Success 大概 2-3 分鐘。

## Step 4.4 — 看執行結果

點進 run 的詳細頁面，再點 `update` job，會看到每個步驟的 log：

- ✅ Checkout
- ✅ Setup Python
- ✅ Install dependencies
- ✅ **Run monitor** ← 重點看這個
- ✅ Commit & push

點開 **Run monitor** 能看到每檔 ETF 的抓取結果：
```
🚀 開始處理 8 檔 ETF（資料日期 2026-04-17）
============================================================

[1/8] 00980A 野村臺灣智慧優選 (野村投信)
   ✅ 抓到 50 檔持股

[2/8] 00985A 野村台灣增強50 (野村投信)
   ✅ 抓到 50 檔持股

[3/8] 00981A 統一台股增長 (統一投信)
   ✅ 抓到 53 檔持股
   📝 今日無異動，未寫入 changelog

[4/8] 00982A 群益台灣精選強棒 (群益投信)
   ✅ 抓到 58 檔持股
...

📊 結果：成功 8 · 無資料 0 · 失敗 0 · 停用 0
```

全部 ✅ 就代表部署成功！

## Step 4.5 — 檢查 repo 有新檔案

回 repo 首頁，應該會看到：
- 新增一筆 commit：`chore: daily update 2026-04-XX`
- 新增 `data/` 資料夾（裡面有 8 個 CSV + 8 個 `_backup/` 資料夾）
- 新增 `reports/` 資料夾（裡面有 HTML 報告）

### 🕐 想補抓之前的歷史資料？沒問題！

系統有**時間智慧**設計，您可以隨意按任何日期順序手動觸發 workflow：

**例子**：您今天（4/17）跑完後，想補抓 4/14、4/15、4/16 的資料：

```
Actions → Run workflow → target_date: 2026-04-14 → Run
Actions → Run workflow → target_date: 2026-04-15 → Run
Actions → Run workflow → target_date: 2026-04-16 → Run
```

結果：
- ✅ 4/14、4/15、4/16 的 `backup/*.csv` 都會被正確建立
- ✅ 4/14、4/15、4/16 的 HTML 報告都會產出
- ✅ 主檔 `data/00981A.csv` 維持 4/17 的內容（**不會被舊資料覆蓋**）
- ✅ `changelog.csv` 不會被污染（補歷史不寫 changelog）
- ✅ 明天（4/18）自動跑時，會用 4/17 當基準正確比對

系統會自動辨識「補歷史」vs「新資料」，您不用擔心順序。

---

# 🎯 Part 5：啟用 GitHub Pages 線上看報告

## Step 5.1 — 設定 Pages

1. Repo → **Settings**
2. 左側選單點 **Pages**
3. **Build and deployment** 區塊：
   - **Source**：選 **Deploy from a branch**
   - **Branch**：
     - 第一個下拉：選 **main**
     - 第二個下拉：選 **/reports** ⭐
     - （如果沒看到 `/reports` 選項，等 1-2 分鐘再刷新頁面）
4. 點 **Save**

## Step 5.2 — 等 Pages 發佈

等 1-3 分鐘，刷新 Pages 頁面會出現：

```
🟢 Your site is live at https://solymx.github.io/monitor_etf_tw_v2/
   Last deployed by solymx ... seconds ago
```

## Step 5.3 — 看線上報告

打開：
```
https://solymx.github.io/monitor_etf_tw_v2/
```

會看到首頁，點任一檔 ETF 進去看詳細報告。

> 💡 **第一次訪問時**，所有持股狀態都是「**首次建立**」，因為還沒有前一天的資料可比對。這是正常的。**明天 17:30** 排程自動跑完後，才會出現真正的「新進/加碼/減碼/清倉」標記。

---

# 🎉 完成！

接下來：
- **每天台灣時間 17:30** GitHub Actions 會自動跑
- 打開 https://solymx.github.io/monitor_etf_tw_v2/ 就能看最新報告
- **禮拜二 17:30 後**才會看到第一批真正的「新進/加碼/減碼」標記（禮拜一跑完建立基準，禮拜二才有得比）

---

# 📋 部署後檢查清單

請花 2 分鐘驗證以下都 OK：

- [ ] Repo 頁面能看到 `core/`、`etfs.yaml`、`main.py` 等檔案
- [ ] Actions 頁面有 `Daily ETF Monitor` workflow
- [ ] 第一次手動跑成功（綠勾）
- [ ] Repo 出現新的 `data/` 和 `reports/` 資料夾
- [ ] Pages 網址 `https://solymx.github.io/monitor_etf_tw_v2/` 能打開
- [ ] 首頁看到 8 檔 ETF 卡片
- [ ] 點任一檔 ETF 進去能看到持股表

---

# 🆘 常見問題排解

### Q1: `git push` 時 `Authentication failed`

您沒用 Personal Access Token。回到 Step 2.7 建一個 PAT。

### Q2: Workflow 跑但 "Permission denied to github-actions[bot]"

Step 3.2 漏做了。去 Settings → Actions → General → 設 **Read and write permissions**。

### Q3: Workflow 跑完顯示 "No changes to commit"

通常是：
- 您指定的日期所有 ETF 都無資料（例如填了非營業日）
- 網路問題全部 fetcher 失敗

去看 Run monitor 那個 step 的 log 看實際原因。

### Q4: Pages 找不到 `/reports` 資料夾選項

因為還沒 run workflow，`/reports` 不存在。先做完 Part 4，等 commit 進去後再來設 Pages。

### Q5: Pages 打開是 404

- 剛設定完要等 1-3 分鐘
- 確認 `/reports/index.html` 存在
- 確認 Pages 設定選的是 `main` + `/reports`

### Q6: 某檔 ETF workflow 裡顯示 "失敗"

- 看 log 找錯誤訊息
- 如果是 `NoDataError` → 該 ETF 當天沒資料，算正常
- 如果是其他錯誤 → 投信可能改了 API，把 log 貼給 Claude 看

### Q7: 我想改排程時間（不要 17:30）

編輯 `.github/workflows/daily_monitor.yml` 第 7 行 cron：

| 台灣時間 | cron |
|---|---|
| 16:00 | `0 8 * * *` |
| 17:00 | `0 9 * * *` |
| 17:30（預設） | `30 9 * * *` |
| 18:00 | `0 10 * * *` |
| 22:00 | `0 14 * * *` |

改完 commit & push：
```bash
git add .github/workflows/daily_monitor.yml
git commit -m "chore: change schedule to XX:XX"
git push
```

### Q8: 我想暫停某檔 ETF

編輯 `etfs.yaml`，把該 ETF 的 `enabled: true` 改 `enabled: false`，commit & push。

### Q9: 某天 workflow 沒跑

GitHub Actions 的排程偶爾會延遲或跳過（尤其尖峰時段）。下次會補跑。
如果連續幾天都沒跑，可能是 repo 超過 60 天沒活動會暫停 —— 只要有 commit 就會恢復。

---

# 📬 遇到問題？

把 workflow 的 run 網址貴給 Claude，例如：
```
https://github.com/solymx/monitor_etf_tw_v2/actions/runs/12345678
```

Claude 會教您怎麼看 log、怎麼修。

祝部署順利 🚀
