"""異動日誌：為特定 ETF 累積記錄每日持股異動。

用途：
    想長期觀察某檔 ETF 的經理人操作風格時使用。相較於 data/<CODE>_backup/
    每日完整快照，這個模組只記錄「有異動的筆數」，累積到單一檔案方便長期分析。

檔案格式（以 00981A 為例）：
    data/00981A_changelog.csv
        日期, 股票代號, 股票名稱, 狀態, 股數變化, 今日股數, 今日權重

    只記錄 4 種狀態：
        新進（新建倉）、加碼、減碼、清倉
    不記錄：持平、首次建立

分析範例（您可以用 pandas）：
    import pandas as pd
    log = pd.read_csv("data/00981A_changelog.csv")

    # 哪些股票最常被加碼？
    log[log["狀態"] == "加碼"]["股票名稱"].value_counts().head(10)

    # 某支股票的買賣歷史
    log[log["股票名稱"] == "台積電"].sort_values("日期")

    # 每月換股頻率
    log["月份"] = log["日期"].str[:7]
    log.groupby(["月份", "狀態"]).size().unstack()
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 要記錄的異動狀態（排除「持平」和「首次建立」）
TRACKED_STATUSES = {"新進", "加碼", "減碼", "清倉"}

# 日誌檔的欄位順序（固定）
LOG_COLUMNS = [
    "日期",
    "股票代號",
    "股票名稱",
    "狀態",
    "股數變化",
    "今日股數",
    "今日權重",
]


def append_changes(
    df_merged: pd.DataFrame,
    code: str,
    date_str: str,
    data_dir: Path,
) -> tuple[Path, int]:
    """把當日異動追加到該 ETF 的 changelog。

    Args:
        df_merged: comparator.compare() 的輸出（含「狀態」「股數變化」欄位）
        code: ETF 代號，例如 "00981A"
        date_str: 資料日期 YYYY-MM-DD
        data_dir: 資料主目錄，通常是 ./data

    Returns:
        (changelog 檔案路徑, 本次新增的筆數)
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / f"{code}_changelog.csv"

    # 1. 過濾出異動列
    mask = df_merged["狀態"].isin(TRACKED_STATUSES)
    changes = df_merged[mask].copy()

    if changes.empty:
        return log_path, 0

    # 2. 組成 changelog 列（用 .get 避免缺欄位時炸掉）
    new_rows = pd.DataFrame({
        "日期": date_str,
        "股票代號": changes["股票代號"].astype(str),
        "股票名稱": changes["股票名稱"].astype(str),
        "狀態": changes["狀態"],
        "股數變化": changes.get(
            "股數變化",
            pd.Series(0, index=changes.index),
        ).astype(float).astype(int),
        "今日股數": changes["股數"].astype(float).astype(int),
        "今日權重": changes["權重"].astype(float).round(4),
    })

    # 3. 讀既有 log（若有）並去重（同一天同一支股票只保留一筆）
    if log_path.exists():
        old_log = pd.read_csv(
            log_path,
            encoding="utf-8-sig",
            dtype={"股票代號": str},  # 避免 "0050" 變 50
        )
        # 移除同一天同一支股票的舊記錄（避免重跑時重複）
        dedupe_mask = ~(
            (old_log["日期"] == date_str)
            & (old_log["股票代號"].isin(new_rows["股票代號"]))
        )
        old_log = old_log[dedupe_mask]
        combined = pd.concat([old_log, new_rows], ignore_index=True)
    else:
        combined = new_rows

    # 4. 確保欄位順序固定，按日期排序
    combined = combined[LOG_COLUMNS].sort_values(
        ["日期", "股票代號"], ascending=[True, True]
    ).reset_index(drop=True)

    combined.to_csv(log_path, index=False, encoding="utf-8-sig")
    return log_path, len(new_rows)
