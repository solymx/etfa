"""HTML 報表產生器。

取代原本每個 .py 檔都內嵌一大段 HTML template 的做法，統一一份：
    - 單檔 ETF 日報（generate_daily_report）
    - 首頁索引（generate_index）
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from .comparator import (
    STATUS_DOWN,
    STATUS_EXIT,
    STATUS_FIRST,
    STATUS_FLAT,
    STATUS_NEW,
    STATUS_UP,
)

# ============================================================================
# 共用樣式
# ============================================================================

_CSS = """
* { box-sizing: border-box; }
body {
  background: #f5f7fa;
  font-family: "Microsoft JhengHei", -apple-system, BlinkMacSystemFont, sans-serif;
  color: #2c3e50;
  margin: 0;
  padding: 20px;
}
.container {
  max-width: 1100px;
  margin: 0 auto;
  background: #fff;
  padding: 28px 32px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
h1, h2 { margin: 0 0 16px 0; }
h1 { font-size: 24px; }
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #eef2f7;
}
.meta { color: #7f8c8d; font-size: 13px; }
.nav-link {
  display: inline-block;
  padding: 6px 14px;
  background: #ecf0f1;
  border-radius: 6px;
  text-decoration: none;
  color: #34495e;
  font-size: 13px;
}
.nav-link:hover { background: #dfe6e9; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
th {
  background: #34495e;
  color: #fff;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
}
td { padding: 10px 12px; border-bottom: 1px solid #ecf0f1; }
tr:hover { background: #fafbfc; }
.text-end { text-align: right; font-variant-numeric: tabular-nums; }
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.badge-new   { background: #e74c3c; }
.badge-up    { background: #e67e22; }
.badge-down  { background: #27ae60; }
.badge-exit  { background: #95a5a6; }
.badge-flat  { background: #bdc3c7; }
.badge-first { background: #3498db; }
.text-up   { color: #c0392b; font-weight: 600; }
.text-down { color: #16a085; font-weight: 600; }
.footer { margin-top: 20px; color: #95a5a6; font-size: 12px; text-align: right; }
"""

_BADGE_MAP = {
    STATUS_NEW: "badge-new",
    STATUS_UP: "badge-up",
    STATUS_DOWN: "badge-down",
    STATUS_EXIT: "badge-exit",
    STATUS_FLAT: "badge-flat",
    STATUS_FIRST: "badge-first",
}


def _fmt_int(v) -> str:
    """把數字格式化成千分位字串；0 或 NaN 顯示 "-"。"""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return "-"
    return f"{n:,}" if n else "-"


def _render_change(change: float) -> str:
    """把股數變化渲染成帶顏色的 HTML。"""
    if not change:
        return '<span class="meta">-</span>'
    if change > 0:
        return f'<span class="text-up">▲ {int(change):,}</span>'
    return f'<span class="text-down">▼ {int(abs(change)):,}</span>'


# ============================================================================
# 單檔 ETF 日報
# ============================================================================

def generate_daily_report(
    df: pd.DataFrame,
    code: str,
    name: str,
    issuer: str,
    output_path: Path,
    search_date: str,
) -> None:
    """產出單檔 ETF 的 HTML 日報。

    Args:
        df: compare() 的輸出
        code: ETF 代號，例如 "00980A"
        name: ETF 中文簡稱
        issuer: 發行投信
        output_path: HTML 檔案輸出路徑
        search_date: 資料日期字串
    """
    rows_html = []
    for _, row in df.iterrows():
        status = row.get("狀態", "-")
        badge_cls = _BADGE_MAP.get(status, "badge-flat")
        change = row.get("股數變化", 0)
        weight = row.get("權重", 0)
        rows_html.append(f"""
          <tr>
            <td><span class="badge {badge_cls}">{status}</span></td>
            <td>{row['股票代號']}</td>
            <td>{row['股票名稱']}</td>
            <td class="text-end">{_fmt_int(row['股數'])}</td>
            <td class="text-end">{_render_change(change)}</td>
            <td class="text-end">{weight:.2f}%</td>
          </tr>
        """)

    # 摘要統計
    changes = df[df["狀態"].isin([STATUS_NEW, STATUS_UP, STATUS_DOWN, STATUS_EXIT])]
    summary = (
        f'今日異動 <strong>{len(changes)}</strong> 筆'
        if len(changes) else "今日持股無變化"
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{code} {name} · 持股追蹤</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div>
        <h1>📊 {code} {name}</h1>
        <div class="meta">{issuer} · 資料日期 {search_date} · {summary}</div>
      </div>
      <a class="nav-link" href="index.html">← 回首頁</a>
    </div>
    <table>
      <thead>
        <tr>
          <th>狀態</th><th>代號</th><th>名稱</th>
          <th class="text-end">持有股數</th>
          <th class="text-end">較上次增減</th>
          <th class="text-end">權重</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    <div class="footer">
      產生時間 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
      · <a href="{code}_trend.html">查看歷史趨勢</a>
    </div>
  </div>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


# ============================================================================
# 首頁索引
# ============================================================================


def _render_watchlist_widget(watchlist_alerts: list[dict] | None) -> str:
    """產 watchlist 的 HTML widget。沒有 watchlist 時回空字串。"""
    if not watchlist_alerts:
        return ""

    items_html = []
    for w in watchlist_alerts:
        code = w["code"]
        name = w["name"]
        note = w.get("note", "")
        alerts = w.get("alerts", [])

        if alerts:
            alerts_html = " · ".join(
                f"<strong>{a['etf']}</strong> {a['status']}"
                + (f" ({a['weight']:.2f}%)" if a.get("weight") else "")
                for a in alerts
            )
            cls = "has-alert"
            icon = "⚠️"
            alert_text = f"<div class='alerts'>{alerts_html}</div>"
        else:
            cls = "no-alert"
            icon = "✓"
            alert_text = "<div class='alerts'>無異動</div>"

        note_html = f" <small>({note})</small>" if note else ""
        items_html.append(f"""
          <div class="watch-item {cls}">
            <span class="stock">{icon} <a href="stocks/{code}.html">{code} {name}</a>{note_html}</span>
            {alert_text}
          </div>
        """)

    return f"""
    <div class="watchlist-widget">
      <h2>🌟 我的關心清單</h2>
      {''.join(items_html)}
    </div>
    """


def generate_index(
    etf_summaries: list[dict],
    output_path: Path,
    watchlist_alerts: list[dict] | None = None,
) -> None:
    """產出首頁索引 HTML。

    Args:
        etf_summaries: 每筆元素為 dict，至少包含：
            code, name, issuer, category, status (success/failed/disabled),
            num_changes, error (如果 failed), last_update
        watchlist_alerts: 關心清單今日狀況，每筆包含：
            {code, name, note, alerts: [{etf, status, weight, diff}, ...]}
    """
    # 按 issuer 分組
    groups: dict[str, list[dict]] = {}
    for s in etf_summaries:
        groups.setdefault(s["issuer"], []).append(s)

    sections_html = []
    for issuer, items in sorted(groups.items()):
        cards = []
        for s in items:
            if s["status"] == "success":
                change_txt = (
                    f"<span class='badge badge-up'>{s['num_changes']} 筆異動</span>"
                    if s["num_changes"] > 0
                    else "<span class='badge badge-flat'>無異動</span>"
                )
                link = f"<a href='{s['code']}.html' class='nav-link'>查看 →</a>"
            elif s["status"] == "no_data":
                change_txt = "<span class='badge badge-flat'>💤 假日/無資料</span>"
                # 若之前曾經成功過，就有舊 HTML 可以連過去
                link = f"<a href='{s['code']}.html' class='nav-link'>歷史 →</a>"
            elif s["status"] == "disabled":
                change_txt = "<span class='badge badge-flat'>未啟用</span>"
                link = ""
            else:
                change_txt = f"<span class='badge badge-exit'>抓取失敗</span>"
                link = f"<span class='meta' title='{s.get('error','')}'>⚠️</span>"

            cards.append(f"""
              <tr>
                <td><strong>{s['code']}</strong></td>
                <td>{s['name']}</td>
                <td>{change_txt}</td>
                <td>{s.get('last_update','-')}</td>
                <td class="text-end">{link}</td>
              </tr>
            """)

        sections_html.append(f"""
          <h2>{issuer}</h2>
          <table>
            <thead>
              <tr>
                <th>代號</th><th>名稱</th><th>今日狀態</th>
                <th>最後更新</th><th class="text-end"></th>
              </tr>
            </thead>
            <tbody>{''.join(cards)}</tbody>
          </table>
        """)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>台灣主動式 ETF 持股監控</title>
  <style>{_CSS}
    .watchlist-widget {{
      background: #fefce8; border: 1px solid #fde68a;
      border-radius: 8px; padding: 16px 20px; margin-bottom: 24px;
    }}
    .watchlist-widget h2 {{ margin-top: 0; color: #92400e; }}
    .watch-item {{
      padding: 8px 0; border-bottom: 1px dashed #fde68a;
    }}
    .watch-item:last-child {{ border-bottom: none; }}
    .watch-item .stock {{ font-weight: bold; }}
    .watch-item .alerts {{
      font-size: 0.9em; color: #555; margin-top: 4px;
    }}
    .watch-item.has-alert {{ color: #991b1b; }}
    .watch-item.no-alert {{ color: #6b7280; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <h1>📈 台灣主動式 ETF 持股監控</h1>
      <span>
        <a class="nav-link" href="exposure.html">跨 ETF 曝險強度 →</a>
        &nbsp;|&nbsp;
        <a class="nav-link" href="stocks/index.html">所有股票 →</a>
      </span>
    </div>
    <div class="meta" style="margin-bottom: 20px;">
      追蹤 {len(etf_summaries)} 檔 ETF（其中 {sum(1 for s in etf_summaries if s['status']=='success')} 檔正常更新）
    </div>
    {_render_watchlist_widget(watchlist_alerts)}
    {''.join(sections_html)}
    <div class="footer">產生時間 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
  </div>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
