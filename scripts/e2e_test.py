"""端對端整合測試。

不實際呼叫投信 API（Actions runner 可能被擋），改用 mock 資料驗證：
  fetcher 格式 → validate → compare → save → report → analyzer → exposure → index

這個測試跑完應該會在 reports/ 產出完整的 demo HTML，讓您預覽效果。
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from core import analyzer, comparator, exposure, reporter, storage  # noqa: E402
from core.models import validate_holdings_df  # noqa: E402

DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"


def make_mock_df(holdings: list[tuple[str, str, int, float]]) -> pd.DataFrame:
    """用 (股票代號, 名稱, 股數, 權重) 的 list 產生 DataFrame。"""
    df = pd.DataFrame(
        holdings, columns=["股票代號", "股票名稱", "股數", "權重"]
    )
    return validate_holdings_df(df, source="mock")


# ========== 用三天的歷史資料模擬 00980A ==========
# 前天、昨天、今天 — 故意加入加碼/減碼/清倉/新進
day_t2 = [  # 兩天前
    ("2330", "台積電", 1_000_000, 30.0),
    ("2454", "聯發科", 500_000, 15.0),
    ("2317", "鴻海", 800_000, 10.0),
    ("3034", "聯詠", 200_000, 8.0),
    ("2303", "聯電", 600_000, 5.0),
    ("2891", "中信金", 300_000, 4.0),
]
day_t1 = [  # 昨天（加碼台積電、減碼聯電、清倉中信金、新進智邦）
    ("2330", "台積電", 1_200_000, 32.0),
    ("2454", "聯發科", 500_000, 15.0),
    ("2317", "鴻海", 800_000, 10.0),
    ("3034", "聯詠", 200_000, 8.0),
    ("2303", "聯電", 400_000, 3.0),
    ("2345", "智邦", 150_000, 6.0),
]
day_t0 = [  # 今天（繼續加碼台積電、減碼鴻海、新進台達電）
    ("2330", "台積電", 1_400_000, 34.0),
    ("2454", "聯發科", 500_000, 15.0),
    ("2317", "鴻海", 600_000, 7.5),
    ("3034", "聯詠", 200_000, 8.0),
    ("2303", "聯電", 400_000, 3.0),
    ("2345", "智邦", 200_000, 8.0),
    ("2308", "台達電", 300_000, 9.0),
]

# ========== 00981A 模擬：與 00980A 有部分持股重疊，用來測曝險聚合 ==========
etf_981_today = [
    ("2330", "台積電", 2_000_000, 25.0),
    ("2454", "聯發科", 800_000, 18.0),
    ("2345", "智邦", 400_000, 12.0),
    ("2308", "台達電", 250_000, 10.0),
    ("3037", "欣興", 300_000, 6.0),
]
# ========== 00985A 模擬（測 3 檔 ETF 的曝險聚合）==========
etf_985_today = [
    ("2330", "台積電", 1_500_000, 28.0),
    ("2454", "聯發科", 600_000, 14.0),
    ("2317", "鴻海", 900_000, 11.0),
    ("2308", "台達電", 400_000, 9.5),
]


def run():
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    # === Phase 1: 模擬 00980A 連續三天的快照 ===
    print("📅 模擬 00980A 三天歷史...")
    today = date.today()
    code = "00980A"

    # 先清理舊資料避免污染
    import shutil
    for p in [
        DATA_DIR / f"{code}.csv",
        DATA_DIR / f"{code}_backup",
    ]:
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)

    # 第 1 天
    df1 = make_mock_df(day_t2)
    old = comparator.load_previous(DATA_DIR / f"{code}.csv")
    _ = comparator.compare(df1, old)
    storage.save_snapshot(df1, code, DATA_DIR)
    # 手動把備份檔重命名成兩天前的日期
    backup_dir = DATA_DIR / f"{code}_backup"
    auto_backup = backup_dir / f"{today.strftime('%Y-%m-%d')}.csv"
    correct_backup = backup_dir / f"{(today - timedelta(days=2)).strftime('%Y-%m-%d')}.csv"
    if auto_backup.exists():
        auto_backup.rename(correct_backup)

    # 第 2 天
    df2 = make_mock_df(day_t1)
    old = comparator.load_previous(DATA_DIR / f"{code}.csv")
    _ = comparator.compare(df2, old)
    storage.save_snapshot(df2, code, DATA_DIR)
    auto_backup = backup_dir / f"{today.strftime('%Y-%m-%d')}.csv"
    correct_backup = backup_dir / f"{(today - timedelta(days=1)).strftime('%Y-%m-%d')}.csv"
    if auto_backup.exists():
        auto_backup.rename(correct_backup)

    # 第 3 天（今天）
    df3 = make_mock_df(day_t0)
    old = comparator.load_previous(DATA_DIR / f"{code}.csv")
    df_merged = comparator.compare(df3, old)
    storage.save_snapshot(df3, code, DATA_DIR)

    print("\n📊 00980A 今日比對結果：")
    print(df_merged[["股票代號", "股票名稱", "股數", "股數變化", "狀態"]].to_string(index=False))

    # 檢查結果：應該看到「加碼台積電」、「減碼鴻海」、「新進台達電」
    assert "加碼" in df_merged["狀態"].values, "應該要有加碼"
    assert "減碼" in df_merged["狀態"].values, "應該要有減碼"
    assert "新進" in df_merged["狀態"].values, "應該要有新進"
    print("\n✅ 比對邏輯驗證通過")

    # 產 HTML 日報
    reporter.generate_daily_report(
        df=df_merged,
        code=code,
        name="野村臺灣智慧優選",
        issuer="野村投信",
        output_path=REPORTS_DIR / f"{code}.html",
        search_date=str(today),
    )
    print(f"✅ 日報產出：reports/{code}.html")

    # 產歷史趨勢（應該有 3 天資料）
    result = analyzer.analyze(
        code=code,
        name="野村臺灣智慧優選",
        backup_dir=DATA_DIR / f"{code}_backup",
        output_path=REPORTS_DIR / f"{code}_trend.html",
    )
    print(f"✅ 趨勢圖產出（共 {result['num_snapshots']} 筆快照）")

    # === Phase 2: 補 00981A 和 00985A 今日資料（用來測曝險）===
    for c, name, holdings in [
        ("00981A", "統一台股增長", etf_981_today),
        ("00985A", "野村台灣增強50", etf_985_today),
    ]:
        df = make_mock_df(holdings)
        old = comparator.load_previous(DATA_DIR / f"{c}.csv")
        merged = comparator.compare(df, old)
        storage.save_snapshot(df, c, DATA_DIR)
        reporter.generate_daily_report(
            df=merged, code=c, name=name,
            issuer="野村投信" if c.startswith("0098") else "統一投信",
            output_path=REPORTS_DIR / f"{c}.html",
            search_date=str(today),
        )
        analyzer.analyze(
            code=c, name=name,
            backup_dir=DATA_DIR / f"{c}_backup",
            output_path=REPORTS_DIR / f"{c}_trend.html",
        )
        print(f"✅ {c} 完成")

    # === Phase 3: 產首頁 & 曝險 ===
    summaries = [
        {
            "code": "00980A", "name": "野村臺灣智慧優選",
            "issuer": "野村投信", "category": "taiwan_stock",
            "status": "success", "num_changes": 3,
            "last_update": str(today), "error": "",
        },
        {
            "code": "00985A", "name": "野村台灣增強50",
            "issuer": "野村投信", "category": "taiwan_stock",
            "status": "success", "num_changes": 0,
            "last_update": str(today), "error": "",
        },
        {
            "code": "00981A", "name": "統一台股增長",
            "issuer": "統一投信", "category": "taiwan_stock",
            "status": "success", "num_changes": 0,
            "last_update": str(today), "error": "",
        },
        {
            "code": "00982A", "name": "群益台灣精選強棒",
            "issuer": "群益投信", "category": "taiwan_stock",
            "status": "failed", "num_changes": 0,
            "last_update": str(today), "error": "Connection timeout",
        },
        {
            "code": "00992A", "name": "群益台灣科技創新",
            "issuer": "群益投信", "category": "taiwan_stock",
            "status": "disabled", "num_changes": 0,
            "last_update": "-", "error": "",
        },
    ]
    reporter.generate_index(summaries, REPORTS_DIR / "index.html")
    print("✅ 首頁產出：reports/index.html")

    agg = exposure.aggregate_exposure(
        [("00980A", "野村臺灣智慧優選"),
         ("00981A", "統一台股增長"),
         ("00985A", "野村台灣增強50")],
        DATA_DIR, REPORTS_DIR / "exposure.html",
    )
    print(f"✅ 曝險報表產出（{len(agg)} 檔個股）")
    print("\n🎯 曝險強度前 5 名：")
    print(agg.head().to_string(index=False))

    print("\n" + "=" * 60)
    print("🎉 整合測試全部通過")


if __name__ == "__main__":
    run()
