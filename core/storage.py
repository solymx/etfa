"""檔案儲存與備份。

檔案配置（以 00980A 為例）：
    data/00980A.csv              ← 最新快照（下次比對基準）
    data/00980A_backup/          ← 歷史快照
        2026-04-19.csv
        2026-04-20.csv
        ...

歷史快照用 YYYY-MM-DD 當檔名，方便 analyzer 直接按日期排序讀取。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def save_snapshot(
    df: pd.DataFrame,
    code: str,
    data_dir: Path,
    backup_suffix: str = "_backup",
    target_date: str | None = None,
    update_main: bool = True,
) -> tuple[Path | None, Path]:
    """儲存快照到歷史資料夾，並選擇性更新主檔。

    Args:
        df: 要儲存的持股 DataFrame
        code: ETF 代號
        data_dir: 資料主目錄
        backup_suffix: backup 資料夾後綴（預設 "_backup"）
        target_date: 資料日期 YYYY-MM-DD（預設今天，用來命名 backup 檔）
        update_main: 是否更新主 CSV（補歷史時應該為 False）

    Returns:
        (主檔案路徑 or None, 歷史備份路徑)
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    main_path = data_dir / f"{code}.csv"
    backup_dir = data_dir / f"{code}{backup_suffix}"
    backup_dir.mkdir(exist_ok=True)

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")
    backup_path = backup_dir / f"{target_date}.csv"

    # 備份用原始欄位（不帶 狀態/股數變化 這些比對產生的欄位）
    cols_to_save = [
        c for c in ["股票代號", "股票名稱", "股數", "權重", "股價", "市值"]
        if c in df.columns
    ]
    df_save = df[cols_to_save].copy()

    # 只存「目前持有」的部位（股數 > 0），不然「清倉」那些會被當作基準
    df_save = df_save[df_save["股數"] > 0].reset_index(drop=True)

    # 永遠寫 backup（補歷史也有用）
    df_save.to_csv(backup_path, index=False, encoding="utf-8-sig")

    # 只有在 update_main=True 時才覆蓋主檔
    main_written = None
    if update_main:
        df_save.to_csv(main_path, index=False, encoding="utf-8-sig")
        main_written = main_path

    return main_written, backup_path


def find_baseline_snapshot(
    code: str,
    data_dir: Path,
    target_date: str,
    backup_suffix: str = "_backup",
) -> tuple[Path | None, str | None]:
    """找「時間智慧」的比對基準：
    從 backup 資料夾找「日期嚴格小於 target_date 的最大日期」那個 CSV。

    Args:
        code: ETF 代號
        data_dir: 資料主目錄
        target_date: 目標日期 YYYY-MM-DD
        backup_suffix: backup 資料夾後綴

    Returns:
        (baseline csv 路徑, 基準日期字串) 或 (None, None) 若找不到

    範例：
        backup/ 裡有 2026-04-15.csv、2026-04-17.csv、2026-04-18.csv
        target_date = "2026-04-18" → 回 2026-04-17.csv（最接近且比較舊的）
        target_date = "2026-04-16" → 回 2026-04-15.csv
        target_date = "2026-04-15" → 回 (None, None)（沒有更舊的了）
    """
    backup_dir = Path(data_dir) / f"{code}{backup_suffix}"
    if not backup_dir.exists():
        return None, None

    candidates = []
    for csv_file in backup_dir.glob("*.csv"):
        # 檔名應為 YYYY-MM-DD.csv
        date_str = csv_file.stem
        # 基本格式檢查
        if len(date_str) == 10 and date_str.count("-") == 2:
            if date_str < target_date:  # 字串比較對 YYYY-MM-DD 格式有效
                candidates.append((date_str, csv_file))

    if not candidates:
        return None, None

    # 取最大（最接近 target_date）
    candidates.sort(reverse=True)
    date_str, path = candidates[0]
    return path, date_str


def get_latest_snapshot_date(
    code: str,
    data_dir: Path,
    backup_suffix: str = "_backup",
) -> str | None:
    """取得 backup 資料夾中最新的快照日期（判斷是否在補歷史用）。"""
    backup_dir = Path(data_dir) / f"{code}{backup_suffix}"
    if not backup_dir.exists():
        return None

    dates = []
    for csv_file in backup_dir.glob("*.csv"):
        date_str = csv_file.stem
        if len(date_str) == 10 and date_str.count("-") == 2:
            dates.append(date_str)

    if not dates:
        return None
    return max(dates)
