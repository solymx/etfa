"""復華投信 fetcher。

適用 ETF：00991A 復華台灣未來50、00998A 復華全球金融股票入息

來源：https://www.fhtrust.com.tw/api/assetsExcel/<etf_code>/<YYYYMMDD>
     回傳 Excel 檔（非 JSON）。

⚠️ 復華的 ETF 代號是內部命名（例如 "ETF23"），需查官網確認每檔對應關係。
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd

from ..exceptions import NoDataError
from ..http import http
from ..models import validate_holdings_df

BASE_URL = "https://www.fhtrust.com.tw/api/assetsExcel"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko)"
    ),
}


def fetch(etf_code: str, date_str: str | None = None, **_) -> pd.DataFrame:
    """抓取復華 ETF 持股（Excel 格式）。

    Args:
        etf_code: 復華內部代號，例如 "ETF23"
        date_str: YYYYMMDD，預設今天

    Returns:
        統一格式的 DataFrame
    """
    if not etf_code:
        raise ValueError("fhtrust fetcher 需要 etf_code 參數")

    if date_str is None:
        date_str = date.today().strftime("%Y%m%d")

    source = f"fhtrust/{etf_code}"
    url = f"{BASE_URL}/{etf_code}/{date_str}"

    resp = http.get(url, headers=_HEADERS)
    # 404 通常表示當天還沒有資料（假日或尚未揭露）
    if resp.status_code == 404:
        raise NoDataError(f"[{source}] {date_str} 查無資料（假日或尚未揭露）")
    resp.raise_for_status()

    # 檔案可能回 0 byte，這時 pd.read_excel 會噴 Empty file 錯誤
    if len(resp.content) < 100:
        raise NoDataError(f"[{source}] {date_str} 下載內容為空")

    # 先讀原始內容定位表頭所在列（復華的 Excel 有標題、備註等前置列）
    raw = pd.read_excel(io.BytesIO(resp.content), header=None)

    header_row = None
    for i, row in raw.iterrows():
        if "證券名稱" in row.values:
            header_row = i
            break

    if header_row is None:
        raise ValueError(
            f"[{source}] 找不到 '證券名稱' 欄位（Excel 格式可能變動）"
        )

    df = pd.read_excel(io.BytesIO(resp.content), skiprows=header_row)
    df = df.dropna(how="all")

    # 排除合計、備註列（第一欄通常是代號/名稱）
    first_col = df.columns[0]
    df = df[~df[first_col].astype(str).str.contains("合計|備註|註", na=False)]

    # 欄位名稱直接交給 validate_holdings_df 處理（別名表在 core/models.py）
    # 復華曾見過的欄位組合：
    #   - ['股票代號', '股票名稱', '股數', '金額', '權重(%)']
    #   - ['證券代號', '證券名稱', '持股股數', '持股比例(%)']
    # 兩種都會被別名表自動統一
    return validate_holdings_df(df, source=source)
