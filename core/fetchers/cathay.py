"""國泰投信 fetcher。

✅ API 已確認（2026-04-19 實測）

📍 資料來源
    GET https://cwapi.cathaysite.com.tw/api/ETF/GetETFDetailStockList
    Query: FundCode=EA, SearchDate=YYYY-MM-DD

🔑 關於 Bearer token
    國泰 API 要求帶 Bearer token，但實測是「匿名訪客 token」（nameid=4374396，
    unique_name 為空），有效期約兩年（2026-04-15 → 2028-04）。
    我們把它寫死在 _DEFAULT_TOKEN，可用 MONITOR_ETF_CATHAY_TOKEN 環境變數覆蓋。
    萬一 token 過期、API 改認證方式，請到國泰官網重新抓並更新此常數。

🗂️ FundCode 對照表
    國泰 ETF 不是用 "00400A" 而是用內部簡碼（兩到三個字母）：
        00400A 國泰台股動能高息 → "EA"
    其他 ETF 代號需在 etfs.yaml 的 params.fund_code 填對應簡碼

🎯 可支援的 ETF
    Phase 2 目標：00400A
    未來國泰若出新主動式 ETF，只要知道 FundCode 就能加進 etfs.yaml
"""

from __future__ import annotations

import os
from datetime import date

import pandas as pd

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

API_URL = "https://cwapi.cathaysite.com.tw/api/ETF/GetETFDetailStockList"

# 訪客 token（約 2028 年到期；可用環境變數覆蓋）
_DEFAULT_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJuYW1laWQiOiI0Mzc0Mzk2IiwidW5pcXVlX25hbWUiOiIiLCJyb2xlIjoiMCIs"
    "IkVDSUQiOiIwIiwiU2Vzc2lvbklkIjoiIiwibmJmIjoxNzc2NTg2OTUzLCJleHAiOjE4MzY1ODY4OTMs"
    "ImlhdCI6MTc3NjU4Njk1M30.9CuQ3TancsfnfcIuRZZf0P_LdL9qStNu85VwUJ040c8"
)


def _build_headers() -> dict:
    token = os.environ.get("MONITOR_ETF_CATHAY_TOKEN", _DEFAULT_TOKEN)
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.cathaysite.com.tw",
        "Referer": "https://www.cathaysite.com.tw/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "authorization": f"Bearer {token}",
    }


def fetch(
    fund_code: str,
    search_date: str | None = None,
    **_,
) -> pd.DataFrame:
    """抓取國泰 ETF 持股。

    Args:
        fund_code: 國泰內部簡碼（例：00400A 用 "EA"）
        search_date: YYYY-MM-DD，預設今天

    Returns:
        統一格式的 DataFrame
    """
    if not fund_code:
        raise ValueError("cathay fetcher 需要 fund_code 參數")

    if search_date is None:
        search_date = str(date.today())

    source = f"cathay/{fund_code}"
    params = {"FundCode": fund_code, "SearchDate": search_date}

    resp = http.get(API_URL, params=params, headers=_build_headers())

    # 401/403 → token 過期或認證變動
    if resp.status_code in (401, 403):
        raise RuntimeError(
            f"[{source}] 國泰 API 認證失敗 (HTTP {resp.status_code})。"
            "Bearer token 可能已過期，請到 https://www.cathaysite.com.tw 的 ETF "
            "頁面重抓 token，更新 core/fetchers/cathay.py 的 _DEFAULT_TOKEN "
            "或設環境變數 MONITOR_ETF_CATHAY_TOKEN。"
        )
    resp.raise_for_status()

    data = resp.json()

    # 國泰 API 回傳格式（2026-04-19 實測確認）：
    # {"result": [...], "returnCode": "2000", "success": true, "returnMessage": null}
    # 每筆 item: {"stockCode": "2330", "stockName": "台積電",
    #            "volumn": "436,000", "weights": "6.99"}
    if not data.get("success"):
        raise RuntimeError(
            f"[{source}] 國泰 API 回傳 success=False, "
            f"returnCode={data.get('returnCode')}, "
            f"returnMessage={data.get('returnMessage')}"
        )

    stocks = data.get("result")

    if not isinstance(stocks, list):
        raise ValueError(
            f"[{source}] result 欄位不是 list（實際是 {type(stocks).__name__}）。"
            "API 結構可能改版，請重新檢查。"
        )

    if not stocks:
        raise NoDataError(
            f"[{source}] {search_date} 無持股資料（假日或尚未揭露）"
        )

    df = pd.DataFrame(stocks)

    # validate_holdings_df 自動處理欄位別名：
    # stockCode→股票代號、stockName→股票名稱、volumn→股數、weights→權重
    # 若國泰未來加新欄位，在 core/models.py COLUMN_ALIASES 補一行即可
    return validate_holdings_df(df, source=source)
