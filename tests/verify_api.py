"""ifind API 接口验证脚本.

逐个调用 ifind HTTP API 并打印原始返回结果，
用于确认接口连通性和返回数据格式。
"""

import json
import sys
import time

import requests

BASE_URL = "https://quantapi.51ifind.com"
REFRESH_TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""

if not REFRESH_TOKEN:
    print("用法: python verify_api.py <refresh_token>")
    sys.exit(1)

session = requests.Session()
session.headers["Content-Type"] = "application/json"


def get_token() -> str:
    """获取 access_token."""
    r = session.post(
        f"{BASE_URL}/api/v1/get_access_token",
        headers={"refresh_token": REFRESH_TOKEN},
    )
    body = r.json()
    print(f"errorcode: {body.get('errorcode')}")
    print(f"errmsg: {body.get('errmsg')}")
    token = body.get("data", {}).get("access_token", "")
    expired = body.get("data", {}).get("expired_time", "")
    print(f"access_token: {token[:20]}...")
    print(f"expired_time: {expired}")
    return token


def set_token(token: str) -> None:
    """设置后续请求的 access_token."""
    session.headers["access_token"] = token


def pretty(data: dict, max_rows: int = 3) -> None:
    """格式化输出 JSON，对 tables 数据限制行数."""
    tables = data.get("tables", [])
    for t in tables:
        if not isinstance(t, dict):
            continue
        tbl = t.get("table", {})
        if not isinstance(tbl, dict):
            continue
        rows = tbl.get("table_data", [])
        if isinstance(rows, list) and len(rows) > max_rows:
            tbl["table_data"] = rows[:max_rows]
            tbl["_truncated"] = f"共 {len(rows)} 行，仅显示前 {max_rows} 行"
    print(json.dumps(data, indent=2, ensure_ascii=False))


def verify_p03797() -> None:
    """验证概念人气明细接口."""
    print("\n" + "=" * 60)
    print("验证 2: data_pool p03797 概念人气明细")
    print("=" * 60)

    # 先用验证清单中的参数格式 (date/tjzq)
    data = {
        "reportname": "p03797",
        "functionpara": {"date": "20260602", "tjzq": "近一周"},
        "outputpara": "p03797_f001,p03797_f002,p03797_f009,p03797_f010",
    }
    r = session.post(f"{BASE_URL}/api/v1/data_pool", json=data)
    body = r.json()
    print(f"errorcode: {body.get('errorcode')}")
    print("返回数据（前3行）:")
    pretty(body)

    time.sleep(0.2)

    # 再用 client.py 中的参数格式 (p03797_f002/p03797_f003) 对比
    print("\n--- 对比：client.py 参数格式 ---")
    data2 = {
        "reportname": "p03797",
        "functionpara": {
            "p03797_f002": "20260602",
            "p03797_f003": "近一周",
        },
        "outputpara": "p03797_f001,p03797_f002,p03797_f009,p03797_f010",
    }
    r2 = session.post(f"{BASE_URL}/api/v1/data_pool", json=data2)
    body2 = r2.json()
    print(f"errorcode: {body2.get('errorcode')}")
    print("返回数据（前3行）:")
    pretty(body2)


def verify_p03798() -> None:
    """验证板块热门成分股接口."""
    print("\n" + "=" * 60)
    print("验证 3: data_pool p03798 板块热门成分股")
    print("=" * 60)

    # 先用验证清单中的参数格式 (date/tjzq/hy)
    data = {
        "reportname": "p03798",
        "functionpara": {
            "date": "20260602",
            "tjzq": "近一周",
            "hy": "芯片概念",
        },
        "outputpara": "jydm,jydm_mc,p03798_f001,p03798_f012,p03798_f016",
    }
    r = session.post(f"{BASE_URL}/api/v1/data_pool", json=data)
    body = r.json()
    print(f"errorcode: {body.get('errorcode')}")
    print("返回数据（前3行）:")
    pretty(body)

    time.sleep(0.2)

    # 再用 client.py 中的参数格式对比
    print("\n--- 对比：client.py 参数格式 ---")
    data2 = {
        "reportname": "p03798",
        "functionpara": {
            "p03798_f001": "20260602",
            "p03798_f002": "芯片概念",
            "p03798_f003": "近一周",
        },
        "outputpara": "jydm,jydm_mc,p03798_f001,p03798_f012,p03798_f016",
    }
    r2 = session.post(f"{BASE_URL}/api/v1/data_pool", json=data2)
    body2 = r2.json()
    print(f"errorcode: {body2.get('errorcode')}")
    print("返回数据（前3行）:")
    pretty(body2)


def verify_history_quotation() -> None:
    """验证历史日K线接口."""
    print("\n" + "=" * 60)
    print("验证 4: cmd_history_quotation 历史日K线")
    print("=" * 60)

    data = {
        "codes": "300033.SZ",
        "indicators": "open,close,high,low,volume,amount",
        "startdate": "2026-05-26",
        "enddate": "2026-06-02",
        "functionpara": {"Interval": "D"},
    }
    r = session.post(
        f"{BASE_URL}/api/v1/cmd_history_quotation",
        json=data,
    )
    body = r.json()
    print(f"errorcode: {body.get('errorcode')}")
    print("返回数据:")
    pretty(body)


def verify_high_frequency() -> None:
    """验证高频1分钟K线接口."""
    print("\n" + "=" * 60)
    print("验证 5: high_frequency 开盘5分钟K线")
    print("=" * 60)

    data = {
        "codes": "300033.SZ",
        "indicators": (
            "open,high,low,close,volume,amount,changeRatio,LB"
        ),
        "starttime": "2026-06-02 09:30:00",
        "endtime": "2026-06-02 09:35:00",
        "functionpara": {"Interval": "1"},
    }
    r = session.post(
        f"{BASE_URL}/api/v1/high_frequency", json=data
    )
    body = r.json()
    print(f"errorcode: {body.get('errorcode')}")
    print("返回数据:")
    pretty(body, max_rows=10)


def verify_trade_dates() -> None:
    """验证交易日查询接口."""
    print("\n" + "=" * 60)
    print("验证 6: get_trade_dates 交易日查询")
    print("=" * 60)

    # 查询含周末的日期范围
    data = {
        "marketcode": "212001",
        "functionpara": {
            "mode": "1",
            "dateType": "0",
            "period": "D",
            "dateFormat": "0",
        },
        "startdate": "2026-05-30",
        "enddate": "2026-06-03",
    }
    r = session.post(
        f"{BASE_URL}/api/v1/get_trade_dates", json=data
    )
    body = r.json()
    print(f"errorcode: {body.get('errorcode')}")
    print("返回数据:")
    pretty(body)


def main() -> None:
    """执行所有接口验证."""
    print("ifind API 接口验证")
    print("=" * 60)

    # 1. Token 验证
    print("验证 1: Token 获取")
    print("-" * 60)
    token = get_token()
    set_token(token)

    time.sleep(0.2)

    # 2. p03797
    verify_p03797()
    time.sleep(0.2)

    # 3. p03798
    verify_p03798()
    time.sleep(0.2)

    # 4. 历史日K线
    verify_history_quotation()
    time.sleep(0.2)

    # 5. 高频K线
    verify_high_frequency()
    time.sleep(0.2)

    # 6. 交易日
    verify_trade_dates()

    print("\n" + "=" * 60)
    print("全部验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
