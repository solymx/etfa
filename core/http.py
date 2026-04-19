"""共用 HTTP client。

為什麼需要這層？
    有些投信網站（例如野村）的 SSL 憑證缺少 Subject Key Identifier，
    在較嚴格的 Python/OpenSSL 環境（Python 3.13, Kali Linux）會驗證失敗。
    但 GitHub Actions 的 Ubuntu runner 和舊版 Python 不會遇到。

    這個模組封裝 requests，提供三層 fallback：
      1. 正常 SSL 驗證
      2. 用 certifi 的 CA bundle 重試
      3. 只有在環境變數 MONITOR_ETF_ALLOW_INSECURE=1 時才關閉驗證

使用方式與 requests 相同：
    from core.http import http
    resp = http.get(url)
    resp = http.post(url, json=payload)
"""

from __future__ import annotations

import os
import warnings

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _build_session() -> requests.Session:
    """建立帶重試策略的 session。"""
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


_session = _build_session()
_allow_insecure = os.environ.get("MONITOR_ETF_ALLOW_INSECURE") == "1"


def _request(method: str, url: str, **kwargs) -> requests.Response:
    """統一的請求入口，帶 SSL fallback。

    kwargs 直接傳給 requests（timeout, json, headers 等皆可）。
    """
    kwargs.setdefault("timeout", 30)

    # 第一次：正常 SSL 驗證
    try:
        return _session.request(method, url, **kwargs)
    except requests.exceptions.SSLError as e_primary:
        # 第二次：改用 certifi 的 CA bundle
        try:
            import certifi
            return _session.request(
                method, url, verify=certifi.where(), **kwargs
            )
        except ImportError:
            pass
        except requests.exceptions.SSLError:
            pass

        # 第三次：若使用者允許不安全模式，才關閉驗證
        if _allow_insecure:
            warnings.warn(
                f"⚠️  SSL 驗證失敗，改用 insecure 模式抓取 {url}"
                "（因為設定了 MONITOR_ETF_ALLOW_INSECURE=1）",
                stacklevel=2,
            )
            # 這裡必須壓掉 urllib3 的 InsecureRequestWarning，否則會洗版
            from urllib3.exceptions import InsecureRequestWarning
            warnings.simplefilter("ignore", InsecureRequestWarning)
            return _session.request(method, url, verify=False, **kwargs)

        # 三層 fallback 都失敗：拋出更友善的錯誤訊息
        raise requests.exceptions.SSLError(
            f"SSL 驗證失敗：{e_primary}\n"
            f"💡 如果您確定在安全網路環境下執行，可以設環境變數繞過：\n"
            f"   export MONITOR_ETF_ALLOW_INSECURE=1\n"
            f"   然後重新執行 python main.py"
        ) from e_primary


class _HttpClient:
    def get(self, url: str, **kwargs) -> requests.Response:
        return _request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return _request("POST", url, **kwargs)


http = _HttpClient()
