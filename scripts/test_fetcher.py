"""單一 fetcher 快速測試工具。

用途：您抓到某家投信的 API、Claude 寫完 fetcher 後，
      用這個工具單獨測試該 fetcher 是否真的能抓到資料。
      比起跑 main.py 更輕量（不會動 data/、不產 HTML）。

用法：
    python scripts/test_fetcher.py <fetcher_name> [--date YYYY-MM-DD] [--params key=value ...]

範例：
    # 測試野村（用最新日期）
    python scripts/test_fetcher.py nomura --params fund_id=00980A

    # 指定日期（自動幫您轉 search_date / date_str 兩種格式）
    python scripts/test_fetcher.py nomura --params fund_id=00980A --date 2026-04-17
    python scripts/test_fetcher.py fhtrust --params etf_code=ETF23 --date 2026-04-17

    # 測試國泰
    python scripts/test_fetcher.py cathay --params fund_code=EA --date 2026-04-17

💡 提示：週末或假日跑會遇到 NoDataError（因為投信沒揭露），這是正常的。
       要驗證某個 fetcher 是否能動，請用 --date 指定一個營業日（例 2026-04-17 週五）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.fetchers import REGISTRY, get_fetcher  # noqa: E402


def parse_params(pairs: list[str]) -> dict:
    """把 ["key=value", ...] 轉成 dict。"""
    result = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"--params 格式錯誤：'{pair}' 應為 key=value")
        k, v = pair.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fetcher_name",
        choices=sorted(REGISTRY.keys()),
        help="要測試的 fetcher 名稱",
    )
    parser.add_argument(
        "--params",
        nargs="*",
        default=[],
        help="傳給 fetcher 的參數（可多個）：--params fund_code=ABC",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="指定日期 YYYY-MM-DD（自動轉成各 fetcher 需要的格式）。"
             "例：--date 2026-04-17",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        help="顯示前 N 筆持股（預設 10）",
    )
    args = parser.parse_args()

    params = parse_params(args.params)

    # 如果有 --date，自動傳 search_date（YYYY-MM-DD）和 date_str（YYYYMMDD）
    # 兩種格式，fetcher 會自己取用它要的那個
    if args.date:
        params.setdefault("search_date", args.date)
        params.setdefault("date_str", args.date.replace("-", ""))

    print(f"🧪 測試 fetcher: {args.fetcher_name}")
    print(f"📦 傳入參數: {params}")
    print("=" * 60)

    try:
        fetcher_fn = get_fetcher(args.fetcher_name)
        df = fetcher_fn(**params)
    except NotImplementedError as e:
        print(f"⚠️  骨架未填：{e}")
        sys.exit(2)
    except Exception as e:
        print(f"❌ 失敗：{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ===== 檢驗結果 =====
    print(f"\n✅ 抓到 {len(df)} 筆持股")
    print(f"📊 欄位：{list(df.columns)}")
    print(f"\n📈 前 {args.show} 大持股（按權重排序）：")
    df_sorted = df.sort_values("權重", ascending=False).head(args.show)
    print(df_sorted.to_string(index=False))

    total_weight = df["權重"].sum()
    print(f"\n💯 總權重：{total_weight:.2f}%  "
          f"（合理範圍：85%~100%，剩餘為現金/其他）")

    if total_weight < 50 or total_weight > 110:
        print(f"⚠️  警告：總權重不太合理，請檢查 API 回應與欄位對應")

    print("\n🎉 測試通過")


if __name__ == "__main__":
    main()
