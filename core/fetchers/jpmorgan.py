"""摩根投信 fetcher（⚠️ 待實作 - 需要您抓到真實 API 後填入）

📍 已知資訊
    ETF：00401A 台灣鑫收益、00989A 大美國領先科技（海外）
    頁面：https://www.jpmrich.com.tw/
    摩根某些基金持股需登入，若遇登入牆改抓公開的前十大或試 ezmoney

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
API_URL = ""  # 例：https://api.jpmrich.com.tw/fund/holdings
METHOD = "GET"  # 或 "POST"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    ),
    "Referer": "https://www.jpmrich.com.tw/",
    # TODO: 若需要 Origin / Cookie / Auth header，在這裡加
}


def fetch(fund_code: str, **_) -> pd.DataFrame:
    """抓取摩根投信 ETF 持股。

    Args:
        fund_code: 摩根投信內部 ETF 代號（從 etfs.yaml params.fund_code 傳入）

    Returns:
        統一格式的 DataFrame（股票代號、股票名稱、股數、權重）
    """
    if not API_URL:
        raise NotImplementedError(
            "jpmorgan fetcher 尚未實作。請參考檔案開頭 TODO 區塊，或見 "
            "docs/PHASE2_INVESTIGATION.md 與 docs/FIND_API_SOP.md"
        )

    source = f"jpmorgan/{fund_code}"

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
