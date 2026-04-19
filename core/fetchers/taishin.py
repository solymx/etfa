"""台新投信 fetcher。

✅ 已實作（2026-04-19）

📍 資料來源
    台新 ETF 頁面是傳統 ASP.NET MVC（server-side rendering），沒有獨立 API。
    持股表直接嵌在 HTML 裡：
        GET https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/{ETF_CODE}
    找頁面中的「股票」表格，欄位：代號、名稱、股數、持股權重

🎯 可支援的 ETF
    00986A 主動台新龍頭成長
    00987A 主動台新優勢成長
    （台新未來若推出更多主動 ETF，只要 URL 格式一樣就能直接用）

⚠️ 注意事項
    - 股票代號後帶 " TT" 後綴（台股代號格式），需清掉
    - HTML 有多個 table（期貨、現金、國家配置、股票…），要找 header 含「股數」、
      「持股權重」的那張
"""

from __future__ import annotations

import pandas as pd
from bs4 import BeautifulSoup

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

BASE_URL = "https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9",
}


def fetch(etf_code: str, **_) -> pd.DataFrame:
    """抓取台新 ETF 持股（解析 HTML 頁面）。

    Args:
        etf_code: ETF 代號，直接用台股代號如 "00987A"、"00986A"

    Returns:
        統一格式的 DataFrame
    """
    if not etf_code:
        raise ValueError("taishin fetcher 需要 etf_code 參數")

    source = f"taishin/{etf_code}"
    url = f"{BASE_URL}/{etf_code}"

    resp = http.get(url, headers=_HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 找出「股票」表格：
    # 頁面裡有多張 table，特徵是 header 同時包含「股數」和「持股權重」
    stock_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "股數" in headers and "持股權重" in headers:
            # 再確認不是期貨表（期貨也有持股權重，但沒有「代號」「名稱」同時出現）
            if "代號" in headers and "名稱" in headers:
                stock_table = table
                break

    if stock_table is None:
        raise NoDataError(
            f"[{source}] 找不到股票持股表格（可能頁面格式變動或 ETF 尚未揭露）"
        )

    # 解析 table
    rows_data = []
    for tr in stock_table.find("tbody").find_all("tr") if stock_table.find("tbody") \
            else stock_table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        code, name, shares, weight = cells[0], cells[1], cells[2], cells[3]

        # 跳過合計列（"股票合計"、空代號）
        if not code or "合計" in code or "合計" in name:
            continue

        # 清掉 " TT" 後綴（例：「2330 TT」→「2330」）
        code = code.replace(" TT", "").strip()

        # 權重字串 "6.6613%" → "6.6613"（validate_holdings_df 會再轉 float）
        weight = weight.replace("%", "").strip()

        rows_data.append({
            "股票代號": code,
            "股票名稱": name,
            "股數": shares,
            "權重": weight,
        })

    if not rows_data:
        raise NoDataError(f"[{source}] 股票表格內無資料")

    df = pd.DataFrame(rows_data)
    return validate_holdings_df(df, source=source)
