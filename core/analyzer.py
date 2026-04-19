"""通用歷史趨勢分析器。

原本 ana981a.py 只能分析 00981A，這裡改成吃任意 ETF 代號，
從 data/<code>_backup/*.csv 讀所有歷史快照，產生趨勢圖。
"""

from __future__ import annotations

import glob
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .reporter import _CSS


def analyze(
    code: str,
    name: str,
    backup_dir: Path,
    output_path: Path,
    window_days: int = 10,
) -> dict:
    """分析某檔 ETF 的歷史持股趨勢。

    Args:
        code: ETF 代號，例如 "00981A"
        name: ETF 中文簡稱
        backup_dir: 歷史 CSV 所在的資料夾，檔名格式 YYYY-MM-DD.csv
        output_path: 輸出 HTML 路徑
        window_days: 重點加/減碼對比窗格天數

    Returns:
        摘要 dict（供 main.py 彙總用）：
            {
                "code": ...,
                "num_snapshots": 快照數,
                "top_increase": [...],  # 權重增加前 N 檔
                "top_decrease": [...],
            }
    """
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return {"code": code, "num_snapshots": 0, "status": "no_data"}

    files = sorted(glob.glob(str(backup_dir / "*.csv")))
    if len(files) < 2:
        # 資料不足，產一個空報表避免 404
        _write_empty_report(code, name, output_path, files)
        return {"code": code, "num_snapshots": len(files), "status": "insufficient"}

    # ===== 讀取所有快照 =====
    frames = []
    for fp in files:
        try:
            date_str = Path(fp).stem  # YYYY-MM-DD
            report_date = pd.to_datetime(date_str)
        except Exception:
            continue
        try:
            df = pd.read_csv(fp, dtype={"股票代號": str})
            df["日期"] = report_date
            frames.append(df)
        except Exception as e:
            print(f"   ⚠️  讀取 {fp} 失敗: {e}")

    if len(frames) < 2:
        _write_empty_report(code, name, output_path, files)
        return {"code": code, "num_snapshots": len(frames), "status": "insufficient"}

    full_df = pd.concat(frames, ignore_index=True).sort_values(
        ["股票代號", "日期"]
    )
    full_df["股數"] = pd.to_numeric(full_df["股數"], errors="coerce").fillna(0)
    full_df["權重"] = pd.to_numeric(full_df["權重"], errors="coerce").fillna(0)

    # ===== 抓取最新 / 對比日 =====
    dates = sorted(full_df["日期"].unique())
    latest_date = pd.Timestamp(dates[-1])
    target_past = latest_date - pd.Timedelta(days=window_days)
    past_date = pd.Timestamp(
        min(dates, key=lambda d: abs(pd.Timestamp(d) - target_past))
    )
    actual_window = (latest_date - past_date).days

    df_latest = full_df[full_df["日期"] == latest_date][
        ["股票代號", "股票名稱", "股數", "權重"]
    ]
    df_past = full_df[full_df["日期"] == past_date][
        ["股票代號", "股數", "權重"]
    ].rename(columns={"股數": "股數_舊", "權重": "權重_舊"})

    cmp = pd.merge(df_latest, df_past, on="股票代號", how="outer").fillna(0)

    # 股票名稱補洞（清倉後最新沒有）
    name_map = full_df.drop_duplicates("股票代號").set_index("股票代號")[
        "股票名稱"
    ].to_dict()
    cmp["股票名稱"] = cmp["股票名稱"].replace("", pd.NA).fillna(
        cmp["股票代號"].map(name_map)
    )
    cmp["權重變動"] = cmp["權重"] - cmp["權重_舊"]

    top_inc = cmp[cmp["權重變動"] > 0].nlargest(10, "權重變動")
    top_dec = cmp[cmp["權重變動"] < 0].nsmallest(10, "權重變動")

    # ===== 準備每檔股票的趨勢資料（Plotly 用）=====
    trend_dict = {}
    for stock_code in df_latest["股票代號"].unique():
        rows = full_df[full_df["股票代號"] == stock_code].sort_values("日期")
        if rows.empty:
            continue
        trend_dict[stock_code] = {
            "name": rows.iloc[-1]["股票名稱"],
            "dates": rows["日期"].dt.strftime("%Y-%m-%d").tolist(),
            "weights": rows["權重"].round(3).tolist(),
            "shares": rows["股數"].astype(int).tolist(),
        }

    # ===== 產出 HTML =====
    _write_trend_report(
        code=code,
        name=name,
        latest_date=latest_date,
        past_date=past_date,
        actual_window=actual_window,
        num_snapshots=len(frames),
        top_inc=top_inc,
        top_dec=top_dec,
        df_latest=df_latest,
        trend_dict=trend_dict,
        output_path=output_path,
    )

    return {
        "code": code,
        "num_snapshots": len(frames),
        "status": "ok",
        "top_increase": top_inc.head(3).to_dict("records"),
        "top_decrease": top_dec.head(3).to_dict("records"),
    }


def _fmt_pct(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "-"
    return f"{f:+.2f}%"


def _top_table(df: pd.DataFrame, css_class: str) -> str:
    if df.empty:
        return "<p class='meta'>期間內無顯著變動</p>"
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"<tr><td>{r['股票代號']}</td><td>{r['股票名稱']}</td>"
            f"<td class='text-end {css_class}'>{_fmt_pct(r['權重變動'])}</td>"
            f"<td class='text-end'>{r['權重']:.2f}%</td></tr>"
        )
    return (
        "<table><thead><tr><th>代號</th><th>名稱</th>"
        "<th class='text-end'>權重變動</th><th class='text-end'>目前權重</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _write_trend_report(
    *,
    code: str,
    name: str,
    latest_date,
    past_date,
    actual_window,
    num_snapshots,
    top_inc,
    top_dec,
    df_latest,
    trend_dict,
    output_path: Path,
) -> None:
    # 股票選擇按鈕（按權重降冪）
    sorted_stocks = df_latest.sort_values("權重", ascending=False)
    tags = "".join(
        f'<div class="tag" onclick=\'showTrend("{r["股票代號"]}", this)\'>'
        f'{r["股票代號"]} {r["股票名稱"]}</div>'
        for _, r in sorted_stocks.iterrows()
        if r["股票代號"] in trend_dict
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{code} {name} · 歷史趨勢</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    {_CSS}
    .tags {{
      display: flex; flex-wrap: wrap; gap: 6px;
      padding: 14px; background: #f8f9fa; border-radius: 8px; margin: 16px 0;
    }}
    .tag {{
      padding: 5px 12px; background: #fff; border: 1px solid #ddd;
      border-radius: 20px; cursor: pointer; font-size: 13px;
    }}
    .tag:hover {{ background: #3498db; color: #fff; border-color: #3498db; }}
    .tag.active {{ background: #3498db; color: #fff; border-color: #3498db; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
    @media (min-width: 800px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
    .placeholder {{
      text-align: center; padding: 50px; color: #95a5a6;
      border: 2px dashed #dfe4ea; border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div>
        <h1>📈 {code} {name} · 歷史趨勢</h1>
        <div class="meta">
          {num_snapshots} 筆歷史快照 ·
          對比期間 {past_date.strftime('%Y-%m-%d')} → {latest_date.strftime('%Y-%m-%d')}
          （{actual_window} 天）
        </div>
      </div>
      <div>
        <a class="nav-link" href="{code}.html">日報</a>
        <a class="nav-link" href="index.html">首頁</a>
      </div>
    </div>

    <h2>🔄 重點變動</h2>
    <div class="grid">
      <div>
        <h3 style="color:#c0392b;">📈 加碼 Top 10</h3>
        {_top_table(top_inc, 'text-up')}
      </div>
      <div>
        <h3 style="color:#16a085;">📉 減碼 Top 10</h3>
        {_top_table(top_dec, 'text-down')}
      </div>
    </div>

    <h2 style="margin-top: 32px;">📊 單股歷史走勢</h2>
    <p class="meta">點選個股查看權重與股數變化</p>
    <div class="tags">{tags}</div>
    <div id="placeholder" class="placeholder">👆 請點選上方個股</div>
    <div id="charts" style="display:none;">
      <h3 id="chartTitle"></h3>
      <div id="weightChart"></div>
      <div id="sharesChart" style="margin-top: 20px;"></div>
    </div>

    <div class="footer">
      產生時間 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
  </div>

  <script>
    const trendData = {json.dumps(trend_dict, ensure_ascii=False)};
    function showTrend(code, el) {{
      document.querySelectorAll('.tag').forEach(t => t.classList.remove('active'));
      el.classList.add('active');
      document.getElementById('placeholder').style.display = 'none';
      document.getElementById('charts').style.display = 'block';
      const d = trendData[code];
      document.getElementById('chartTitle').innerText =
        code + ' ' + d.name + ' 歷史走勢';
      Plotly.newPlot('weightChart', [{{
        x: d.dates, y: d.weights, mode: 'lines+markers',
        line: {{ color: '#16a085', width: 3 }},
        name: '權重'
      }}], {{
        title: '權重 (%)', hovermode: 'x unified',
        margin: {{ t: 40, b: 40, l: 60, r: 20 }}
      }});
      Plotly.newPlot('sharesChart', [{{
        x: d.dates, y: d.shares, mode: 'lines+markers',
        line: {{ color: '#3498db', width: 3 }},
        name: '股數'
      }}], {{
        title: '持有股數', hovermode: 'x unified',
        margin: {{ t: 40, b: 40, l: 80, r: 20 }}
      }});
    }}
  </script>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def _write_empty_report(
    code: str, name: str, output_path: Path, files: list
) -> None:
    """歷史資料不足時，產一個提示頁。"""
    msg = (
        "需要至少 2 筆歷史快照才能分析趨勢。"
        f"目前有 {len(files)} 筆快照，請等系統累積幾天的資料後再來看。"
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8"><title>{code} {name} · 歷史趨勢</title>
<style>{_CSS}</style></head>
<body><div class="container">
  <div class="header-bar">
    <h1>📈 {code} {name} · 歷史趨勢</h1>
    <a class="nav-link" href="index.html">← 回首頁</a>
  </div>
  <p>{msg}</p>
</div></body></html>"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
