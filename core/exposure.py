"""跨 ETF 曝險強度聚合器。

對應 README 描述：「合計權重 — 這是把所有 ETF 對某持股的權重直接做相加，
代表曝險強度，也就是全部相關的 ETF 都買的話，對於該股票持有的比例是多少。」

邏輯：
    1. 讀取每檔 ETF 最新的 data/<code>.csv
    2. 按股票代號 groupby，權重直接相加，名稱取第一筆，持有 ETF 清單列出來
    3. 產出 reports/exposure.html（可排序）

注意：「合計權重」不等於「加權平均權重」—— 它就是單純相加，
用來看如果一個人把所有相關 ETF 都買了，某檔個股的累積曝險會有多重。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .reporter import _CSS


def aggregate_exposure(
    etf_codes_with_names: list[tuple[str, str]],
    data_dir: Path,
    output_path: Path,
) -> pd.DataFrame | None:
    """彙總所有 ETF 對每檔個股的曝險強度。

    Args:
        etf_codes_with_names: [(code, name), ...] 要納入彙總的 ETF
        data_dir: 存 CSV 的資料夾
        output_path: HTML 輸出路徑

    Returns:
        彙總後的 DataFrame（供測試/除錯用）；失敗時回傳 None
    """
    data_dir = Path(data_dir)
    frames = []

    for code, etf_name in etf_codes_with_names:
        csv_path = data_dir / f"{code}.csv"
        if not csv_path.exists():
            continue
        try:
            df = pd.read_csv(csv_path, dtype={"股票代號": str})
            df["_etf_code"] = code
            df["_etf_name"] = etf_name
            frames.append(df[["股票代號", "股票名稱", "權重", "_etf_code", "_etf_name"]])
        except Exception as e:
            print(f"   ⚠️  讀取 {csv_path} 失敗: {e}")

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined["權重"] = pd.to_numeric(combined["權重"], errors="coerce").fillna(0)

    # ===== 聚合：按股票代號 =====
    agg = combined.groupby("股票代號").agg(
        股票名稱=("股票名稱", "first"),
        合計權重=("權重", "sum"),
        ETF檔數=("_etf_code", "nunique"),
        持有ETF清單=("_etf_code", lambda xs: ", ".join(sorted(set(xs)))),
    ).reset_index()

    agg = agg.sort_values(
        ["ETF檔數", "合計權重"], ascending=[False, False]
    ).reset_index(drop=True)

    # ===== 產 HTML =====
    _write_exposure_report(
        agg=agg,
        num_etfs=len(etf_codes_with_names),
        included_etfs=[code for code, _ in etf_codes_with_names],
        output_path=output_path,
    )

    return agg


def _write_exposure_report(
    *,
    agg: pd.DataFrame,
    num_etfs: int,
    included_etfs: list[str],
    output_path: Path,
) -> None:
    rows = []
    for i, r in agg.iterrows():
        # 讓排名前幾名特別顯眼
        highlight = ' style="background:#fff8e7;"' if i < 5 else ""
        etf_tags = "".join(
            f'<span class="etf-tag">{e}</span>'
            for e in str(r["持有ETF清單"]).split(", ")
        )
        rows.append(f"""
          <tr{highlight}>
            <td class="text-end meta">{i+1}</td>
            <td>{r['股票代號']}</td>
            <td><strong>{r['股票名稱']}</strong></td>
            <td class="text-end">
              <span class="badge badge-new">{r['ETF檔數']} 檔</span>
            </td>
            <td class="text-end text-up">{r['合計權重']:.2f}%</td>
            <td class="etf-list">{etf_tags}</td>
          </tr>
        """)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>跨 ETF 曝險強度</title>
  <style>
    {_CSS}
    .etf-tag {{
      display: inline-block; margin: 1px 3px 1px 0;
      padding: 1px 7px; background: #ecf0f1; border-radius: 3px;
      font-size: 11px; color: #34495e;
    }}
    .etf-list {{ max-width: 320px; }}
    .intro {{
      background: #fef9e7; border-left: 4px solid #f39c12;
      padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;
      font-size: 13px; color: #7d6608;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <h1>🎯 跨 ETF 曝險強度</h1>
      <a class="nav-link" href="index.html">← 回首頁</a>
    </div>

    <div class="intro">
      <strong>什麼是曝險強度？</strong>
      把所有追蹤的 ETF 對同一檔股票的權重直接相加，代表
      「如果把這些 ETF 都買齊，對該股票的累積權重會有多重」。
      <br>
      <span class="meta">
        這是 <strong>合計</strong> 不是 <strong>平均</strong>：
        例如 5 檔 ETF 都持有台積電各 30%，合計權重就是 150%。
      </span>
    </div>

    <div class="meta" style="margin-bottom: 16px;">
      納入計算 <strong>{num_etfs}</strong> 檔 ETF：
      {', '.join(included_etfs)}
      · 共發現 <strong>{len(agg)}</strong> 檔不重複個股
    </div>

    <table>
      <thead>
        <tr>
          <th class="text-end">#</th>
          <th>代號</th>
          <th>名稱</th>
          <th class="text-end">被幾檔持有</th>
          <th class="text-end">合計權重</th>
          <th>持有 ETF</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>

    <div class="footer">
      產生時間 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
  </div>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
