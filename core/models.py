"""統一資料模型。

所有 fetcher 回傳的 DataFrame **必須** 有以下四個欄位：
    股票代號 (str)  — 例如 "2330"，務必是字串避免 "0050" 變 50
    股票名稱 (str)  — 例如 "台積電"
    股數     (float) — 持有股數，已去逗號
    權重     (float) — 權重百分比，例如 25.3 代表 25.3%

選用欄位（若 API 有給則帶上）：
    股價 (float)
    市值 (float)

欄位別名：為了讓 fetcher 不用特地 rename，validate_holdings_df 會自動
把常見別名（例如「權重(%)」→「權重」）統一成規範欄位名。

這個契約用 `validate_holdings_df` 強制執行；任何 fetcher 新加時，
只要通過這個檢查，整條 pipeline 都能處理。
"""

from __future__ import annotations

import pandas as pd

# 必要欄位（所有 fetcher 必須產出）
REQUIRED_COLUMNS = ["股票代號", "股票名稱", "股數", "權重"]

# 選用欄位
OPTIONAL_COLUMNS = ["股價", "市值"]

# 欄位別名對應表：別名 → 規範欄位名
# 新的別名在這裡加一行就行，所有 fetcher 自動受惠
COLUMN_ALIASES = {
    # 權重類別
    "權重(%)": "權重",
    "權重％": "權重",
    "比例": "權重",
    "比例(%)": "權重",
    "持股比例": "權重",
    "持股比例(%)": "權重",
    "NavRate": "權重",
    "weight": "權重",
    "weights": "權重",          # 國泰（注意是複數）
    # 股數類別
    "持有股數": "股數",
    "持股股數": "股數",
    "Share": "股數",
    "shares": "股數",
    "volumn": "股數",           # 國泰（注意是 typo，正確拼法應為 volume）
    "volume": "股數",           # 萬一他哪天改好，也支援
    # 代號類別
    "證券代號": "股票代號",
    "stockCode": "股票代號",
    "stocNo": "股票代號",
    "DetailCode": "股票代號",
    # 名稱類別
    "證券名稱": "股票名稱",
    "stockName": "股票名稱",
    "stocName": "股票名稱",
    "DetailName": "股票名稱",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把常見別名統一成規範欄位名。只改名，不改資料。"""
    rename_map = {
        col: COLUMN_ALIASES[col]
        for col in df.columns
        if col in COLUMN_ALIASES and COLUMN_ALIASES[col] not in df.columns
        # 上面這個條件避免重複命名：如果目標欄位已經存在就不動
    }
    return df.rename(columns=rename_map) if rename_map else df


def validate_holdings_df(df: pd.DataFrame, source: str = "") -> pd.DataFrame:
    """檢查並正規化持股 DataFrame。

    Args:
        df: fetcher 回傳的原始 DataFrame
        source: 來源識別字串（給錯誤訊息用，例如 "nomura/00980A"）

    Returns:
        乾淨的 DataFrame（股票代號轉 str，數值欄位轉 float，去空列）

    Raises:
        ValueError: 缺必要欄位或資料為空
    """
    if df is None or df.empty:
        raise ValueError(f"[{source}] fetcher 回傳空資料")

    # 先套用別名正規化
    df = _normalize_columns(df.copy())

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{source}] 缺少必要欄位 {missing}。"
            f"目前欄位：{list(df.columns)}。"
            f"如果是新的別名，請在 core/models.py 的 COLUMN_ALIASES 登錄。"
        )

    # 股票代號強制為字串並去前後空白（避免 CSV 讀回後 "0050" 變 int 50）
    df["股票代號"] = df["股票代號"].astype(str).str.strip()
    df["股票名稱"] = df["股票名稱"].astype(str).str.strip()

    # 數值欄位：去逗號、轉 float、NaN 補 0
    for col in ["股數", "權重"] + [c for c in OPTIONAL_COLUMNS if c in df.columns]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0)
        )

    # 過濾掉股數 = 0 的雜項列（有些 API 會塞合計列）
    df = df[df["股數"] > 0].reset_index(drop=True)

    if df.empty:
        raise ValueError(f"[{source}] 清洗後無有效資料（全部股數為 0？）")

    return df
