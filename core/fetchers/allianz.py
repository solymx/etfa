"""安聯投信 fetcher（⏸️ 暫緩實作 - 2026-04-19）

📍 已知資訊
    ETF：00984A 安聯台灣高息成長、00993A 安聯台灣
    頁面：https://etf.allianzgi.com.tw/etf-info/E0002?tab=4

📊 2026-04-19 調查結論
    安聯有獨立 API，但有 ASP.NET Core Antiforgery 保護，pure Python 很難繞過：

    API: POST https://etf.allianzgi.com.tw/webapi/api/Fund/GetFundAssets
    Body: {"FundID":"E0002"}
    必要 header: X-XSRF-TOKEN
    必要 cookie: .AspNetCore.Antiforgery.XXX + X-XSRF-TOKEN + TS011e9ff1

    FundID 對照：
        00984A → E0001（推測）
        00993A → E0002（已實測頁面能用）

🔧 實測結果（2026-04-19）
    - 「直接 POST」失敗（被擋）
    - 「GET 頁面 → POST」失敗（GET 只拿到 TS011e9ff1 這個 TLS session cookie，
      X-XSRF-TOKEN cookie 不會在初次 GET 時發送）
    - 「GET 根目錄 + GET 頁面 → POST」失敗
    - 前端 JS 可能在某個內部 API 握手時才拿到 token，需要進一步抓網路流量分析

⚠️ 繞不過的根本原因
    前端 JS 裡一定有某段程式碼：
        1. 呼叫某個「取 token」端點（可能藏在 /webapi/api/Antiforgery 或類似路徑）
        2. 把 token 寫進 cookie 和 sessionStorage
        3. 之後才能呼叫 GetFundAssets

    要繞過需要用 Selenium/Playwright 跑真瀏覽器，或逆向前端 JS 找到「取 token」那支。
    以當前架構（純 requests）做不到。

🚀 未來恢復方案（擇一）
    方案 A：Selenium/Playwright
        新增 selenium 依賴，用 headless Chrome 打開頁面讓 JS 執行完，
        再從 driver.get_cookies() 取出完整 cookie 送 API。
        缺點：拖慢 CI、環境依賴複雜

    方案 B：環境變數傳入瀏覽器 cookie
        每天手動去瀏覽器複製 cookie 貼到環境變數，fetcher 直接用。
        缺點：無法全自動化，違背系統核心目的

    方案 C：等安聯改版到較寬鬆的 API
        持續觀察，網站偶爾會換架構

    方案 D：到 ezmoney 基富通看安聯 ETF 是否有上架
        若有，複用既有的 ezmoney fetcher
"""

from __future__ import annotations


def fetch(**_):
    """暫緩實作。見檔案頂端調查結論。"""
    raise NotImplementedError(
        "allianz fetcher 暫緩（2026-04-19）：API 有 ASP.NET Antiforgery CSRF "
        "保護且無法用純 requests 繞過。詳見 core/fetchers/allianz.py 頂端註解。"
    )
