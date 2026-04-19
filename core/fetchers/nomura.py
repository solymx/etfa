"""野村投信 fetcher。

適用 ETF：00980A 野村臺灣智慧優選、00985A 野村台灣增強50、
         00999A 野村臺灣策略高息（皆使用同一 API，僅 FundID 不同）

API：https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets
     POST JSON: {"FundID": "00980A", "SearchDate": "YYYY-MM-DD"}
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

API_URL = "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    ),
    "Content-Type": "application/json",
    "Referer": "https://www.nomurafunds.com.tw/",
    "Origin": "https://www.nomurafunds.com.tw",
}


def fetch(fund_id: str, search_date: str | None = None, **_) -> pd.DataFrame:
    """抓取野村 ETF 持股。

    Args:
        fund_id: 例如 "00980A"
        search_date: "YYYY-MM-DD"，預設今天

    Returns:
        統一格式的 DataFrame
    """
    if search_date is None:
        search_date = str(date.today())

    source = f"nomura/{fund_id}"
    payload = {"FundID": fund_id, "SearchDate": search_date}

    resp = http.post(API_URL, headers=_HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()

    tables = data.get("Entries", {}).get("Data", {}).get("Table", [])
    stock_table = next(
        (t for t in tables if t.get("TableTitle") == "股票"), None
    )
    if not stock_table:
        raise NoDataError(
            f"[{source}] {search_date} 無持股資料（假日或尚未揭露）"
        )

    columns = [col["Name"] for col in stock_table["Columns"]]
    df = pd.DataFrame(stock_table["Rows"], columns=columns)

    # 野村欄位名稱：股票代號、股票名稱、股數、權重、股價、市值
    # 已是統一格式，validate 會處理型態轉換
    return validate_holdings_df(df, source=source)
