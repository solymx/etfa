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
) -> tuple[Path, Path]:
    """儲存今日快照並備份到歷史資料夾。

    Returns:
        (主檔案路徑, 歷史備份路徑)
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    main_path = data_dir / f"{code}.csv"
    backup_dir = data_dir / f"{code}{backup_suffix}"
    backup_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    backup_path = backup_dir / f"{today}.csv"

    # 備份用原始欄位（不帶 狀態/股數變化 這些比對產生的欄位）
    cols_to_save = [
        c for c in ["股票代號", "股票名稱", "股數", "權重", "股價", "市值"]
        if c in df.columns
    ]
    df_save = df[cols_to_save].copy()

    # 只存「目前持有」的部位（股數 > 0），不然「清倉」那些會被當作基準
    df_save = df_save[df_save["股數"] > 0].reset_index(drop=True)

    df_save.to_csv(main_path, index=False, encoding="utf-8-sig")
    df_save.to_csv(backup_path, index=False, encoding="utf-8-sig")

    return main_path, backup_path
