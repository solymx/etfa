"""monitor_etf_tw 核心模組。

各 fetcher 都會回傳統一格式的 DataFrame（見 models.HoldingRow），
由 comparator 做新舊比對，reporter 產出 HTML。
"""
