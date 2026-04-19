"""驗證 validate_holdings_df 的欄位別名功能。

特別驗證這次 bug：野村實際回傳「權重(%)」而非「權重」。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from core.models import validate_holdings_df  # noqa: E402


def test_nomura_real_columns():
    """模擬野村實際回傳的欄位：「權重(%)」應自動轉成「權重」。"""
    df = pd.DataFrame([
        {"股票代號": "2330", "股票名稱": "台積電", "股數": "1,200,000", "權重(%)": "32.5"},
        {"股票代號": "2454", "股票名稱": "聯發科", "股數": "500,000",   "權重(%)": "15.0"},
    ])
    result = validate_holdings_df(df, source="test/nomura")
    assert "權重" in result.columns, "別名未被正規化"
    assert "權重(%)" not in result.columns, "舊欄位名還在"
    assert result["權重"].iloc[0] == 32.5
    assert result["股數"].iloc[0] == 1_200_000  # 逗號被清掉
    assert isinstance(result["股票代號"].iloc[0], str)  # 保持字串型態
    print("✅ 野村欄位別名測試通過")


def test_fhtrust_real_columns():
    """模擬復華 Excel 的欄位：「證券代號」、「持股股數」、「持股比例(%)」。"""
    df = pd.DataFrame([
        {"證券代號": "2330", "證券名稱": "台積電", "持股股數": 1_500_000, "持股比例(%)": 28.0},
        {"證券代號": "0050", "證券名稱": "元大 50", "持股股數": 100_000,   "持股比例(%)": 5.0},
    ])
    result = validate_holdings_df(df, source="test/fhtrust")
    assert list(result.columns)[:4] == ["股票代號", "股票名稱", "股數", "權重"]
    # 確認 0050 沒有被解析成 int 50
    assert result["股票代號"].iloc[1] == "0050"
    print("✅ 復華欄位別名測試通過")


def test_fhtrust_actual_4_17():
    """復華 4/17 實際 Excel 欄位：已經用「股票代號」但權重是「權重(%)」，還多了「金額」欄。

    這是上線實測抓到的真實格式。
    """
    df = pd.DataFrame([
        {"股票代號": "2330", "股票名稱": "台積電", "股數": "1,500,000",
         "金額": "1,500,000,000", "權重(%)": "28.0"},
        {"股票代號": "2454", "股票名稱": "聯發科", "股數": "500,000",
         "金額": "500,000,000", "權重(%)": "15.0"},
    ])
    result = validate_holdings_df(df, source="test/fhtrust_actual")
    assert "權重" in result.columns, "權重(%) 應該被轉成權重"
    assert result["權重"].iloc[0] == 28.0
    # 金額欄沒在別名表也不會擋，只是不會用
    print("✅ 復華 4/17 實測欄位組合測試通過")


def test_ezmoney_real_columns():
    """模擬統一（ezmoney）的欄位：DetailCode / DetailName / Share / NavRate。"""
    df = pd.DataFrame([
        {"DetailCode": "2330", "DetailName": "台積電", "Share": 2_000_000, "NavRate": 25.0},
    ])
    result = validate_holdings_df(df, source="test/ezmoney")
    assert list(result.columns)[:4] == ["股票代號", "股票名稱", "股數", "權重"]
    assert result["權重"].iloc[0] == 25.0
    print("✅ 統一 (ezmoney) 欄位別名測試通過")


def test_already_normalized_passes_through():
    """已經是規範欄位的 DataFrame 應該直接通過，不受影響。"""
    df = pd.DataFrame([
        {"股票代號": "2330", "股票名稱": "台積電", "股數": 1000, "權重": 30.0},
    ])
    result = validate_holdings_df(df, source="test/normalized")
    assert result["權重"].iloc[0] == 30.0
    print("✅ 已規範資料直通測試通過")


def test_missing_required_raises():
    """缺必要欄位應拋出明確錯誤訊息。"""
    df = pd.DataFrame([{"代號": "2330", "名稱": "台積電"}])  # 用錯誤名稱
    try:
        validate_holdings_df(df, source="test/bad")
    except ValueError as e:
        assert "缺少必要欄位" in str(e)
        print("✅ 錯誤訊息測試通過")
        return
    raise AssertionError("應該要拋 ValueError")


if __name__ == "__main__":
    test_nomura_real_columns()
    test_fhtrust_real_columns()
    test_fhtrust_actual_4_17()
    test_ezmoney_real_columns()
    test_already_normalized_passes_through()
    test_missing_required_raises()
    print("\n🎉 所有別名測試通過")
