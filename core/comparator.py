"""持股比對器。

把新舊兩個快照 merge 起來，算出每檔股票的狀態（新進 / 加碼 / 減碼 / 清倉）。
原本每個 .py 檔都各自寫了一份，這裡統一起來。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import validate_holdings_df

# 狀態常數（原 repo 各檔用詞不一，統一規範）
STATUS_NEW = "新進"
STATUS_EXIT = "清倉"
STATUS_UP = "加碼"
STATUS_DOWN = "減碼"
STATUS_FLAT = "持平"
STATUS_FIRST = "首次建立"


def load_previous(csv_path: Path) -> pd.DataFrame | None:
    """讀取指定 CSV 作為比對基準。沒有就回傳 None。

    路徑可以是主檔 data/<code>.csv，也可以是 backup 的某個歷史快照。
    """
    if not csv_path or not csv_path.exists():
        return None
    try:
        # dtype 強制股票代號為字串，避免 "0050" 讀成 50
        df = pd.read_csv(csv_path, dtype={"股票代號": str})
        return validate_holdings_df(df, source=f"load_previous:{csv_path.name}")
    except Exception as e:
        print(f"⚠️  讀取舊檔 {csv_path} 失敗（將視為首次執行）：{e}")
        return None


def compare(df_new: pd.DataFrame, df_old: pd.DataFrame | None) -> pd.DataFrame:
    """比對新舊持股。

    Returns:
        DataFrame 包含欄位：
            股票代號, 股票名稱, 股數, 權重, 股數_舊, 股數變化, 狀態
        （若有選用欄位 股價/市值 也會保留）
    """
    df_new = df_new.copy()

    if df_old is None:
        df_new["股數_舊"] = 0.0
        df_new["股數變化"] = 0.0
        df_new["狀態"] = STATUS_FIRST
        return df_new

    # outer join：新舊都保留，才能看到「清倉」
    merged = pd.merge(
        df_new,
        df_old[["股票代號", "股數"]].rename(columns={"股數": "股數_舊"}),
        on="股票代號",
        how="outer",
    )

    # 對於「全部賣出」的個股，df_new 不會有該列 → 股票名稱、權重等會是 NaN
    # 用舊資料補上名稱，其他數值欄位補 0
    if df_old is not None:
        name_map = df_old.set_index("股票代號")["股票名稱"].to_dict()
        merged["股票名稱"] = merged["股票名稱"].fillna(
            merged["股票代號"].map(name_map)
        ).fillna("(未知)")

    for col in ["股數", "股數_舊", "權重"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)

    merged["股數變化"] = merged["股數"] - merged["股數_舊"]

    def _status(row):
        old = row["股數_舊"]
        curr = row["股數"]
        if old == 0 and curr > 0:
            return STATUS_NEW
        if old > 0 and curr == 0:
            return STATUS_EXIT
        if curr > old:
            return STATUS_UP
        if curr < old:
            return STATUS_DOWN
        return STATUS_FLAT

    merged["狀態"] = merged.apply(_status, axis=1)

    # 排序：異動優先（新進/清倉在最上面），再按權重降冪
    status_order = {
        STATUS_NEW: 0,
        STATUS_UP: 1,
        STATUS_DOWN: 2,
        STATUS_EXIT: 3,
        STATUS_FLAT: 4,
    }
    merged["_sort"] = merged["狀態"].map(status_order).fillna(9)
    merged = merged.sort_values(
        ["_sort", "權重"], ascending=[True, False]
    ).drop(columns="_sort").reset_index(drop=True)

    return merged
