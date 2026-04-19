"""群益投信 fetcher。

適用 ETF：00982A 群益台灣精選強棒、00992A 群益台灣科技創新、
         00997A 群益美國增長

API：https://www.capitalfund.com.tw/CFWeb/api/etf/buyback
     POST JSON: {"fundId": "399", "date": null}
"""

from __future__ import annotations

import pandas as pd

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

API_URL = "https://www.capitalfund.com.tw/CFWeb/api/etf/buyback"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    ),
    "Content-Type": "application/json",
    "Referer": "https://www.capitalfund.com.tw/",
}


def fetch(fund_id: str, date_str: str | None = None, **_) -> pd.DataFrame:
    """抓取群益 ETF 持股。

    Args:
        fund_id: 群益內部 fundId，例如 "399"（⚠️ 原 repo 備註需確認此為哪檔 ETF）
        date_str: 指定日期，預設 None（當日）

    Returns:
        統一格式的 DataFrame
    """
    if not fund_id:
        raise ValueError("capital fetcher 需要 fund_id 參數")

    source = f"capital/{fund_id}"
    payload = {"fundId": fund_id, "date": date_str}

    resp = http.post(API_URL, headers=_HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()

    stocks = data.get("data", {}).get("stocks", [])
    if not stocks:
        raise NoDataError(f"[{source}] 當前無持股資料（假日或尚未揭露）")

    df = pd.DataFrame(stocks)
    # 群益欄位：stocNo, stocName, weight, shareFormat
    df = df[["stocNo", "stocName", "weight", "shareFormat"]]
    df.columns = ["股票代號", "股票名稱", "權重", "股數"]

    return validate_holdings_df(df, source=source)
