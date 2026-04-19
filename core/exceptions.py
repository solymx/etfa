"""專案內部例外定義。

用來區分不同類型的失敗，讓 main.py 可以做不同處理：
  - NoDataError: 投信確實沒有揭露資料（假日、尚未揭露），不算失敗
  - FetcherError: 抓取過程的真正錯誤（網路、API 掛掉、格式變動）
"""


class NoDataError(Exception):
    """來源確認沒有資料（例如週末、假日、尚未揭露）。

    這不是程式或抓取的錯誤，只是今天沒資料，不該算在失敗統計。
    """


class FetcherError(Exception):
    """抓取過程中的真正錯誤（網路、解析、API 格式變動等）。"""
