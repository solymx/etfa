"""第一金投信 fetcher（⏸️ 暫緩實作 - 2026-04-19）

📍 已知資訊
    ETF：00994A 第一金台股趨勢優選
    頁面：https://www.fsitc.com.tw/FundDetail.aspx?ID=182

📊 2026-04-19 調查結論
    第一金頁面是 ASP.NET server-side rendering（類似台新），但持股揭露切成兩塊：

    ❌ 前十大靜態表格（頁面直接渲染）
        - 只有 10 檔、只有資產名稱+比重，【缺股票代號與股數】
        - 資料日期是月底快照（例如 2026/03/31），非每日更新
        - 跟本系統的股票代號比對架構不相容

    ❓ 完整持股表格（空白、需要選日期觸發 AJAX/postback）
        - 頁面上有「資料日期：___ [查詢]」的表單
        - 下面的「### 股票」表格 header 齊全（股票代號/名稱/權重/股數）
        - 但只有點「查詢」後才會被填入資料
        - 尚未取得這個 AJAX 請求的 URL/Payload

🔧 若要繼續實作，請依以下步驟抓 AJAX：
    1. 打開 https://www.fsitc.com.tw/FundDetail.aspx?ID=182
    2. F12 → Network → Fetch/XHR + Preserve log
    3. 捲到「資料日期：___ [查詢]」那一區
    4. 下拉選日期（例：2026/04/16）→ 點「查詢」
    5. Network 找 response 含 `2330` 或 `台積電` 的請求
    6. 右鍵 → Copy as cURL，貼給 Claude

🔍 如何完成此 fetcher：
    1. 依 docs/FIND_API_SOP.md 的步驟抓 API
    2. 把 Request URL / Method / Headers / Payload / Response 貼給 Claude
    3. Claude 會替您填入下方 TODO 區塊
"""

from __future__ import annotations

import pandas as pd

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

# ============================================================================
# TODO ① 調查到 API 後，填入這裡
# ============================================================================
API_URL = ""  # 例：https://api.fsitc.com.tw/fund/holdings
METHOD = "GET"  # 或 "POST"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    ),
    "Referer": "https://www.fsitc.com.tw/etf/etf-info/FS994A",
    # TODO: 若需要 Origin / Cookie / Auth header，在這裡加
}


def fetch(fund_code: str, **_) -> pd.DataFrame:
    """抓取第一金投信 ETF 持股。

    Args:
        fund_code: 第一金投信內部 ETF 代號（從 etfs.yaml params.fund_code 傳入）

    Returns:
        統一格式的 DataFrame（股票代號、股票名稱、股數、權重）
    """
    if not API_URL:
        raise NotImplementedError(
            "firstsino fetcher 尚未實作。請參考檔案開頭 TODO 區塊，或見 "
            "docs/PHASE2_INVESTIGATION.md 與 docs/FIND_API_SOP.md"
        )

    source = f"firstsino/{fund_code}"

    # ========================================================================
    # TODO ② 根據抓到的 API 格式，填入請求邏輯
    # ========================================================================
    # 範例 A：GET + query string
    #   resp = http.get(API_URL, params={"fundCode": fund_code}, headers=_HEADERS)
    # 範例 B：POST + JSON body
    #   resp = http.post(API_URL, headers=_HEADERS, json={"fundCode": fund_code})
    # 範例 C：POST + form data
    #   resp = http.post(API_URL, headers=_HEADERS, data={"fundCode": fund_code})
    resp = http.get(API_URL, params={"fundCode": fund_code}, headers=_HEADERS)
    resp.raise_for_status()
    data = resp.json()

    # ========================================================================
    # TODO ③ 從 JSON 回應抓出持股 list（觀察 response 結構）
    # ========================================================================
    holdings = data.get("data", {}).get("holdings", [])
    if not holdings:
        raise NoDataError(f"[{source}] 當前無持股資料（假日或尚未揭露）")

    # ========================================================================
    # TODO ④ validate_holdings_df 自動處理欄位別名（見 core/models.py）
    # ========================================================================
    df = pd.DataFrame(holdings)
    return validate_holdings_df(df, source=source)
