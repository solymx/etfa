"""Fetcher 註冊表。

每個 fetcher 模組要實作一個叫 `fetch(**params)` 的函式，回傳統一格式的 DataFrame。
這裡用字串名稱對應，讓 etfs.yaml 可以用 fetcher: "nomura" 這種字串指定。

新增 fetcher 的步驟：
    1. 在 core/fetchers/ 下加檔案（如 foobar.py）
    2. 在此檔 import 並註冊到 REGISTRY
    3. 在 etfs.yaml 把對應 ETF 的 fetcher 設成 "foobar"、enabled 改 true
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from . import (
    allianz,
    capital,
    cathay,
    ctbc,
    ezmoney,
    fhtrust,
    firstsino,
    jpmorgan,
    megafund,
    nomura,
    taishin,
    yuanta,
)

REGISTRY: dict[str, Callable[..., pd.DataFrame]] = {
    # Phase 1：已驗證可用
    "nomura": nomura.fetch,       # 野村（API 已確認）
    "ezmoney": ezmoney.fetch,     # 統一（走基富通，API 已確認）
    "capital": capital.fetch,     # 群益（API 已確認）
    "fhtrust": fhtrust.fetch,     # 復華（Excel 已確認）
    # Phase 2：骨架就緒，待您抓 API 後由 Claude 補上
    "allianz": allianz.fetch,     # 安聯
    "cathay": cathay.fetch,       # 國泰
    "ctbc": ctbc.fetch,           # 中國信託
    "firstsino": firstsino.fetch,  # 第一金
    "jpmorgan": jpmorgan.fetch,   # 摩根
    "megafund": megafund.fetch,   # 兆豐
    "taishin": taishin.fetch,     # 台新
    "yuanta": yuanta.fetch,       # 元大
}


def get_fetcher(name: str) -> Callable[..., pd.DataFrame]:
    """依 fetcher 名稱取得實作函式。"""
    if name not in REGISTRY:
        raise ValueError(
            f"未知 fetcher '{name}'，已註冊：{sorted(REGISTRY.keys())}"
        )
    return REGISTRY[name]
