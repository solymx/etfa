"""每支股票的專屬頁面產生器。

為每支「曾被任一 ETF 持有過」的股票，產一個獨立頁面：
    reports/stocks/<股票代號>.html

內容包含：
    1. 今日被哪些 ETF 持有（含權重、今日狀態）
    2. 跨 ETF 的歷史權重趨勢
    3. 時間軸：被買進 / 賣出的歷史事件

資料來源：
    - 所有 ETF 的 data/<CODE>.csv（最新持股）
    - 所有 ETF 的 data/<CODE>_backup/*.csv（歷史快照）
    - 所有 ETF 的 changelog（如果有）
"""

from __future__ import annotations

import glob
import html
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from .reporter import _CSS


def generate_all_stock_pages(
    etfs: list[dict],
    data_dir: Path,
    reports_dir: Path,
    backup_suffix: str = "_backup",
    history_days: int = 30,
    watchlist: list[dict] | None = None,
) -> dict:
    """產生所有股票的專屬頁面。

    Args:
        etfs: 啟用中的 ETF 配置清單（來自 etfs.yaml 的 enabled 項）
        data_dir: 資料主目錄
        reports_dir: 輸出 HTML 目錄
        history_days: 歷史趨勢保留天數
        watchlist: 關心清單（可選，標示用）

    Returns:
        摘要 dict：{"num_stocks": N, "output_dir": path}
    """
    stocks_dir = reports_dir / "stocks"
    stocks_dir.mkdir(parents=True, exist_ok=True)

    # 讀所有 ETF 的歷史資料，組成 { 股票代號: {...} } 結構
    all_stocks = _gather_all_stock_data(
        etfs, data_dir, backup_suffix, history_days
    )

    watchlist_codes = {w["code"] for w in (watchlist or [])}

    # 產每支股票的頁面
    n_written = 0
    for stock_code, info in all_stocks.items():
        html_content = _render_stock_page(
            stock_code=stock_code,
            name=info["name"],
            current_holdings=info["current"],
            history=info["history"],
            is_watchlist=stock_code in watchlist_codes,
        )
        out_path = stocks_dir / f"{stock_code}.html"
        out_path.write_text(html_content, encoding="utf-8")
        n_written += 1

    # 產股票索引頁（方便從首頁跳轉）
    index_html = _render_stocks_index(
        all_stocks, watchlist_codes
    )
    (stocks_dir / "index.html").write_text(index_html, encoding="utf-8")

    return {"num_stocks": n_written, "output_dir": str(stocks_dir)}


def _gather_all_stock_data(
    etfs: list[dict],
    data_dir: Path,
    backup_suffix: str,
    history_days: int,
) -> dict:
    """從各 ETF 的 CSV 聚合出每支股票的跨 ETF 資料。

    Returns:
        {
            "2330": {
                "name": "台積電",
                "current": [  # 最新持股
                    {"etf_code": "00980A", "etf_name": "...",
                     "股數": 100000, "權重": 12.5, "狀態": "加碼",
                     "股數變化": 5000},
                    ...
                ],
                "history": {  # 每 ETF 每日權重
                    "00980A": {"2026-04-14": 12.0, "2026-04-15": 12.5, ...},
                    "00981A": {"2026-04-14": 13.0, ...},
                }
            }
        }
    """
    result = defaultdict(lambda: {
        "name": "",
        "current": [],
        "history": defaultdict(dict),
    })

    # 計算日期門檻，只讀最近 N 天的 backup（避免太慢）
    today = datetime.now().date()

    for etf in etfs:
        code = etf["code"]
        name = etf["name"]

        # 1. 讀主檔（最新持股 + 狀態）
        main_csv = data_dir / f"{code}.csv"
        if main_csv.exists():
            try:
                df = pd.read_csv(main_csv, dtype={"股票代號": str})
                # 主檔只有股票代號/名稱/股數/權重，沒有「狀態」
                # 狀態要從 comparator 的結果推導，但我們這裡簡化：
                # 如果 backup 裡昨天有資料，能算出狀態；否則標「持平」
                yesterday_status = _infer_today_status(
                    code, data_dir, backup_suffix
                )
                for _, row in df.iterrows():
                    sc = str(row["股票代號"]).strip()
                    sn = str(row["股票名稱"]).strip()
                    if not result[sc]["name"]:
                        result[sc]["name"] = sn
                    result[sc]["current"].append({
                        "etf_code": code,
                        "etf_name": name,
                        "股數": float(row["股數"]),
                        "權重": float(row["權重"]),
                        "狀態": yesterday_status.get(sc, "持平"),
                        "股數變化": yesterday_status.get(f"{sc}_diff", 0),
                    })
            except Exception as e:
                print(f"⚠️  讀 {main_csv} 失敗：{e}")

        # 2. 讀 backup 歷史（過去 N 天）
        backup_dir = data_dir / f"{code}{backup_suffix}"
        if backup_dir.exists():
            for csv_file in sorted(backup_dir.glob("*.csv")):
                date_str = csv_file.stem
                try:
                    bdate = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if (today - bdate).days > history_days:
                    continue

                try:
                    df = pd.read_csv(csv_file, dtype={"股票代號": str})
                    for _, row in df.iterrows():
                        sc = str(row["股票代號"]).strip()
                        sn = str(row["股票名稱"]).strip()
                        if not result[sc]["name"]:
                            result[sc]["name"] = sn
                        result[sc]["history"][code][date_str] = float(
                            row["權重"]
                        )
                except Exception as e:
                    print(f"⚠️  讀 {csv_file} 失敗：{e}")

    # 去除 name 為空的（應該不會，但保險）
    return {k: v for k, v in result.items() if v["name"]}


def _infer_today_status(
    code: str, data_dir: Path, backup_suffix: str
) -> dict:
    """推斷主檔相對於最近 backup 的每股狀態和股數變化。

    Returns:
        {股票代號: 狀態字串, 股票代號_diff: 股數變化}
    """
    backup_dir = data_dir / f"{code}{backup_suffix}"
    if not backup_dir.exists():
        return {}

    backups = sorted(backup_dir.glob("*.csv"))
    if len(backups) < 2:
        return {}

    # 取倒數第二個（最接近「前一日」）
    prev_csv = backups[-2]
    main_csv = data_dir / f"{code}.csv"

    try:
        new = pd.read_csv(main_csv, dtype={"股票代號": str})
        old = pd.read_csv(prev_csv, dtype={"股票代號": str})
    except Exception:
        return {}

    old_map = dict(zip(old["股票代號"].astype(str), old["股數"].astype(float)))
    result = {}
    for _, row in new.iterrows():
        sc = str(row["股票代號"]).strip()
        curr = float(row["股數"])
        prev = old_map.get(sc, 0)
        diff = curr - prev
        if prev == 0:
            result[sc] = "新進"
        elif diff > 0:
            result[sc] = "加碼"
        elif diff < 0:
            result[sc] = "減碼"
        else:
            result[sc] = "持平"
        result[f"{sc}_diff"] = int(diff)

    # 處理清倉（老有新沒）
    new_codes = set(new["股票代號"].astype(str))
    for sc, shares in old_map.items():
        if sc not in new_codes and shares > 0:
            result[sc] = "清倉"
            result[f"{sc}_diff"] = int(-shares)

    return result


_STATUS_BADGE = {
    "新進": ("badge-new", "🆕 新進"),
    "加碼": ("badge-up", "📈 加碼"),
    "減碼": ("badge-down", "📉 減碼"),
    "清倉": ("badge-exit", "❌ 清倉"),
    "持平": ("badge-flat", "持平"),
}


def _render_stock_page(
    stock_code: str,
    name: str,
    current_holdings: list[dict],
    history: dict,
    is_watchlist: bool,
) -> str:
    """產生單支股票的 HTML 頁面。"""
    # 按權重降冪排序今日持股
    current_sorted = sorted(
        current_holdings, key=lambda x: x["權重"], reverse=True
    )

    # 算異動數
    n_changes = sum(
        1 for h in current_sorted
        if h["狀態"] in ("新進", "加碼", "減碼")
    )

    # 組今日表格
    rows_html = []
    for h in current_sorted:
        badge_cls, badge_txt = _STATUS_BADGE.get(
            h["狀態"], ("badge-flat", h["狀態"])
        )
        diff = h.get("股數變化", 0)
        diff_txt = ""
        if diff > 0:
            diff_txt = f"+{diff:,}"
        elif diff < 0:
            diff_txt = f"{diff:,}"

        rows_html.append(f"""
        <tr>
          <td><a href="../{html.escape(h['etf_code'])}.html">{html.escape(h['etf_code'])}</a></td>
          <td>{html.escape(h['etf_name'])}</td>
          <td><span class="badge {badge_cls}">{html.escape(badge_txt)}</span></td>
          <td class="text-end">{int(h['股數']):,}</td>
          <td class="text-end">{diff_txt}</td>
          <td class="text-end">{h['權重']:.2f}%</td>
        </tr>
        """)

    # 歷史趨勢圖的資料（Chart.js）
    # 收集所有日期
    all_dates = sorted({
        d for etf_hist in history.values() for d in etf_hist.keys()
    })
    datasets = []
    # 給每條線一個顏色
    palette = [
        "#3b82f6", "#ef4444", "#10b981", "#f59e0b",
        "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
    ]
    for i, (etf_code, weights_by_date) in enumerate(history.items()):
        data = [weights_by_date.get(d, None) for d in all_dates]
        # 轉 None → null for JSON
        data_js = [x if x is not None else None for x in data]
        datasets.append({
            "label": etf_code,
            "data": data_js,
            "borderColor": palette[i % len(palette)],
            "backgroundColor": palette[i % len(palette)] + "33",
            "tension": 0.2,
            "spanGaps": True,
        })

    chart_config = {
        "type": "line",
        "data": {
            "labels": all_dates,
            "datasets": datasets,
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"{stock_code} {name} - 各 ETF 權重變化（近期）",
                },
                "legend": {"position": "bottom"},
            },
            "scales": {
                "y": {
                    "title": {"display": True, "text": "權重 (%)"},
                },
            },
        },
    }

    chart_json = json.dumps(chart_config, ensure_ascii=False)

    watchlist_badge = (
        '<span class="badge badge-watchlist">🌟 關心清單</span>'
        if is_watchlist else ""
    )

    no_current_msg = (
        '<p class="text-muted">目前無 ETF 持有此股。</p>'
        if not current_sorted else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(stock_code)} {html.escape(name)} - 跨 ETF 持股追蹤</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {_CSS}
  <style>
    .badge-watchlist {{ background: #fde68a; color: #92400e; }}
    .chart-container {{ max-width: 900px; margin: 2rem auto; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
  <div class="container">
    <nav class="breadcrumb">
      <a href="../index.html">← 首頁</a> ·
      <a href="index.html">所有股票</a>
    </nav>

    <h1>
      {html.escape(stock_code)} {html.escape(name)}
      {watchlist_badge}
    </h1>
    <p class="meta">
      今日被 <strong>{len(current_sorted)}</strong> 檔 ETF 持有
      · 異動 <strong>{n_changes}</strong> 筆
      · 更新時間 {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </p>

    <h2>📊 各 ETF 當前持股</h2>
    {no_current_msg}
    {"" if not current_sorted else f'''
    <table class="holdings-table">
      <thead>
        <tr>
          <th>ETF</th>
          <th>名稱</th>
          <th>今日狀態</th>
          <th class="text-end">持有股數</th>
          <th class="text-end">較上次增減</th>
          <th class="text-end">權重</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
    '''}

    <h2>📈 權重歷史趨勢</h2>
    <div class="chart-container">
      <canvas id="weightChart"></canvas>
    </div>

    <footer class="footer">
      <small>
        資料來源：各投信官方揭露 · 本頁自動產生，不構成投資建議
      </small>
    </footer>
  </div>

  <script>
    const config = {chart_json};
    new Chart(document.getElementById('weightChart'), config);
  </script>
</body>
</html>
"""


def _render_stocks_index(
    all_stocks: dict, watchlist_codes: set
) -> str:
    """產所有股票的索引頁。"""
    # 按「被多少檔 ETF 持有」排序
    stocks_sorted = sorted(
        all_stocks.items(),
        key=lambda x: (-len(x[1]["current"]), x[0]),
    )

    rows = []
    for sc, info in stocks_sorted:
        n_etf = len(info["current"])
        total_weight = sum(h["權重"] for h in info["current"])
        is_watch = sc in watchlist_codes

        watch_mark = "🌟 " if is_watch else ""
        row_cls = "watchlist-row" if is_watch else ""

        # 列出該股所在的 ETF（短）
        etfs_str = ", ".join(
            sorted(h["etf_code"] for h in info["current"])
        )

        rows.append(f"""
        <tr class="{row_cls}">
          <td>{watch_mark}<a href="{html.escape(sc)}.html"><strong>{html.escape(sc)}</strong></a></td>
          <td><a href="{html.escape(sc)}.html">{html.escape(info['name'])}</a></td>
          <td class="text-end">{n_etf}</td>
          <td class="text-end">{total_weight:.2f}%</td>
          <td><small>{html.escape(etfs_str)}</small></td>
        </tr>
        """)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>所有股票 - 跨 ETF 持股追蹤</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {_CSS}
  <style>
    .watchlist-row {{ background: #fefce8; }}
  </style>
</head>
<body>
  <div class="container">
    <nav class="breadcrumb">
      <a href="../index.html">← 首頁</a>
    </nav>
    <h1>📋 所有被持有的股票</h1>
    <p class="meta">
      共 <strong>{len(stocks_sorted)}</strong> 支股票
      · 🌟 為您關心清單裡的股票
    </p>

    <table class="holdings-table">
      <thead>
        <tr>
          <th>代號</th>
          <th>名稱</th>
          <th class="text-end">持有 ETF 數</th>
          <th class="text-end">曝險強度</th>
          <th>所在 ETF</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
