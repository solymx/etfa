"""統一投信 fetcher（走基富通 ezmoney 網站）。

適用 ETF：00981A 統一台股增長、00988A 統一全球創新、00403A 統一台股升級50
     （統一投信 ETF 的持股多半在 ezmoney 平台揭露）

來源：https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=XXXXX
     頁面內有 <div id="DataAsset" data-content="...JSON...">
"""

from __future__ import annotations

import html as html_lib
import json

import pandas as pd
from bs4 import BeautifulSoup

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

BASE_URL = "https://www.ezmoney.com.tw/ETF/Fund/Info"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    ),
}


def fetch(fund_code: str, **_) -> pd.DataFrame:
    """抓取 ezmoney 上某檔 ETF 的股票持倉。

    Args:
        fund_code: ezmoney 的內部代號，例如 "49YTW"（00981A 的代號）
                   ⚠️ 需實際查詢 ezmoney 網站才知道正確代號

    Returns:
        統一格式的 DataFrame
    """
    if not fund_code:
        raise ValueError("ezmoney fetcher 需要 fund_code 參數")

    source = f"ezmoney/{fund_code}"
    resp = http.get(
        BASE_URL, params={"fundCode": fund_code}, headers=_HEADERS
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    div = soup.find("div", id="DataAsset")
    if not div or not div.get("data-content"):
        raise ValueError(f"[{source}] 找不到 DataAsset div（網頁結構可能有變動）")

    data = json.loads(html_lib.unescape(div["data-content"]))

    stock_details = None
    for item in data:
        if item.get("AssetCode") == "ST":
            stock_details = item.get("Details")
            break

    if not stock_details:
        raise NoDataError(f"[{source}] 當前無股票持倉資料（假日或尚未揭露）")

    # ezmoney 欄位：DetailCode, DetailName, Share, NavRate
    df = pd.DataFrame(stock_details)[
        ["DetailCode", "DetailName", "Share", "NavRate"]
    ]
    df.columns = ["股票代號", "股票名稱", "股數", "權重"]

    return validate_holdings_df(df, source=source)
