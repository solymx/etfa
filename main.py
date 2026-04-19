"""monitor_etf_tw 主入口腳本。

使用方式：
    # 跑全部啟用中的 ETF
    python main.py

    # 只跑單一檔
    python main.py --only 00980A

    # 只跑單一投信的所有 ETF
    python main.py --issuer 野村投信

    # 指定日期（方便補資料）
    python main.py --date 2026-04-18
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

import yaml

from core import analyzer, changelog, comparator, exposure, reporter, storage
from core.exceptions import NoDataError
from core.fetchers import get_fetcher

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "etfs.yaml"


# ============================================================================
# 配置載入
# ============================================================================

def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================================
# 單檔 ETF 的處理 pipeline
# ============================================================================

def process_one(
    etf: dict,
    data_dir: Path,
    reports_dir: Path,
    backup_suffix: str,
    search_date: str,
) -> dict:
    """跑一檔 ETF 的完整流程：fetch → compare → save → report。

    Returns:
        摘要 dict（供首頁彙總 & 終端輸出用）
    """
    code = etf["code"]
    summary = {
        "code": code,
        "name": etf["name"],
        "issuer": etf["issuer"],
        "category": etf.get("category", ""),
        "status": "unknown",
        "num_changes": 0,
        "error": "",
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    if not etf.get("enabled", True):
        summary["status"] = "disabled"
        print(f"   ⏭️  {code} {etf['name']} 已停用，跳過")
        return summary

    try:
        # 1. 呼叫 fetcher
        fetcher_fn = get_fetcher(etf["fetcher"])
        params = dict(etf.get("params") or {})
        # 把 search_date 也傳進去（有些 fetcher 用得到）
        params.setdefault("search_date", search_date)
        params.setdefault("date_str", search_date.replace("-", ""))
        df_new = fetcher_fn(**params)
        print(f"   ✅ 抓到 {len(df_new)} 檔持股")

        # 2. 時間智慧：決定 baseline 和是否要更新主檔
        # 從 backup 找「日期嚴格 < search_date 的最大日期」
        baseline_path, baseline_date = storage.find_baseline_snapshot(
            code, data_dir, search_date, backup_suffix=backup_suffix
        )

        # 判斷是否要更新主檔：
        # 當 search_date 是目前最新的（沒有比它更新的 backup 存在）才更新
        latest_existing = storage.get_latest_snapshot_date(
            code, data_dir, backup_suffix=backup_suffix
        )
        is_catching_up = (
            latest_existing is not None and search_date < latest_existing
        )

        if baseline_date:
            print(f"   📆 比對基準：{baseline_date}")
        else:
            print(f"   📆 比對基準：（無，首次建立）")

        if is_catching_up:
            print(f"   ⏪ 補歷史模式（最新快照 {latest_existing} > {search_date}，不更新主檔與 changelog）")

        old = comparator.load_previous(baseline_path) if baseline_path else None
        df_merged = comparator.compare(df_new, old)

        # 2.5 若有設 track_changelog 且不是補歷史模式，累積異動日誌
        if etf.get("track_changelog", False) and not is_catching_up:
            log_path, n_changes = changelog.append_changes(
                df_merged, code, search_date, data_dir
            )
            if n_changes > 0:
                print(f"   📝 追加 {n_changes} 筆異動到 {log_path.name}")
            else:
                print(f"   📝 今日無異動，未寫入 changelog")

        # 3. 存檔：永遠寫 backup，只在非補歷史時更新主檔
        storage.save_snapshot(
            df_new, code, data_dir,
            backup_suffix=backup_suffix,
            target_date=search_date,
            update_main=not is_catching_up,
        )

        # 4. 產 HTML 日報（補歷史也產，但會覆蓋當日的報告）
        reporter.generate_daily_report(
            df=df_merged,
            code=code,
            name=etf["name"],
            issuer=etf["issuer"],
            output_path=reports_dir / f"{code}.html",
            search_date=search_date,
        )

        # 5. 產歷史趨勢頁（資料不足會自動生成提示頁）
        analyzer.analyze(
            code=code,
            name=etf["name"],
            backup_dir=data_dir / f"{code}{backup_suffix}",
            output_path=reports_dir / f"{code}_trend.html",
        )

        changes_mask = df_merged["狀態"].isin(["新進", "加碼", "減碼", "清倉"])
        summary["num_changes"] = int(changes_mask.sum())
        summary["status"] = "success"

    except NoDataError as e:
        # 假日或尚未揭露：不算失敗，首頁顯示「無資料」
        summary["status"] = "no_data"
        summary["error"] = str(e)
        print(f"   💤 {code} 今日無資料（假日或尚未揭露）")

    except Exception as e:
        summary["status"] = "failed"
        summary["error"] = f"{type(e).__name__}: {e}"
        print(f"   ❌ {code} 處理失敗: {summary['error']}")
        traceback.print_exc()

    return summary


# ============================================================================
# 主流程
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="monitor_etf_tw")
    parser.add_argument("--only", help="只跑指定 ETF 代號")
    parser.add_argument("--issuer", help="只跑指定投信")
    parser.add_argument(
        "--date", default=str(date.today()),
        help="資料日期 YYYY-MM-DD，預設今天",
    )
    parser.add_argument(
        "--skip-index", action="store_true",
        help="跳過產生首頁索引與曝險報表",
    )
    args = parser.parse_args()

    cfg = load_config()
    settings = cfg.get("settings", {})
    data_dir = ROOT / settings.get("data_dir", "data")
    reports_dir = ROOT / settings.get("reports_dir", "reports")
    backup_suffix = settings.get("backup_dir_suffix", "_backup")

    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    etfs = cfg["etfs"]

    # 過濾
    if args.only:
        etfs = [e for e in etfs if e["code"] == args.only]
        if not etfs:
            print(f"找不到 ETF 代號 {args.only}")
            sys.exit(1)
    if args.issuer:
        etfs = [e for e in etfs if e["issuer"] == args.issuer]

    print(f"🚀 開始處理 {len(etfs)} 檔 ETF（資料日期 {args.date}）")
    print("=" * 60)

    summaries = []
    for i, etf in enumerate(etfs, 1):
        print(f"\n[{i}/{len(etfs)}] {etf['code']} {etf['name']} ({etf['issuer']})")
        s = process_one(
            etf, data_dir, reports_dir, backup_suffix, args.date
        )
        summaries.append(s)

    # ====== 產首頁 & 曝險報表 ======
    if not args.skip_index:
        print("\n" + "=" * 60)
        print("📄 產生首頁索引...")
        reporter.generate_index(summaries, reports_dir / "index.html")

        print("🎯 計算跨 ETF 曝險強度...")
        successful = [
            (s["code"], s["name"])
            for s in summaries
            if s["status"] == "success"
        ]
        if successful:
            exposure.aggregate_exposure(
                successful, data_dir, reports_dir / "exposure.html"
            )
            print(f"   ✅ 彙總 {len(successful)} 檔 ETF 的曝險資料")

    # ====== 總結 ======
    print("\n" + "=" * 60)
    ok = sum(1 for s in summaries if s["status"] == "success")
    no_data = sum(1 for s in summaries if s["status"] == "no_data")
    failed = sum(1 for s in summaries if s["status"] == "failed")
    disabled = sum(1 for s in summaries if s["status"] == "disabled")
    print(
        f"📊 結果：成功 {ok} · 無資料 {no_data} "
        f"· 失敗 {failed} · 停用 {disabled}"
    )

    if failed > 0:
        print("\n失敗清單：")
        for s in summaries:
            if s["status"] == "failed":
                print(f"  - {s['code']} {s['name']}: {s['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
