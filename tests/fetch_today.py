"""采集指定交易日的概念人气、成分股、日K线和分钟K线数据并存入 SQLite.

用法::

    python tests/fetch_today.py [YYYYMMDD]

默认采集今日数据。脚本会：
1. 获取概念人气排名 (p03797)
2. 对每个概念获取成分股 (p03798)
3. 获取所有成分股的日K线（近5个交易日）
4. 获取所有成分股的1分钟K线（09:30~09:35）
5. 全部存入 SQLite
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scanner.client import IfindClient
from scanner.config import get_config
from scanner.db import Database
from scanner.models import (
    BoardStock,
    ConceptPopularity,
    DailyKline,
    KlineBar,
)


def load_env(env_path: Path) -> None:
    """手动加载 .env 文件到环境变量."""
    if not env_path.exists():
        print(f"警告: {env_path} 不存在")
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def parse_date(date_str: str) -> str:
    """将日期字符串统一为 YYYYMMDD 格式."""
    d = date_str.replace("-", "").replace("/", "")
    return d


def normalize_date_display(date_str: str) -> str:
    """将 YYYYMMDD 格式转为 YYYY-MM-DD."""
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def fetch_concept_popularity(
    client: IfindClient, date_ymd: str
) -> list[ConceptPopularity]:
    """获取概念人气排名并转换为数据类列表."""
    print(f"\n[1/4] 获取概念人气排名 (p03797) date={date_ymd}")
    rows = client.get_concept_popularity(date_ymd)
    records = []
    for row in rows:
        popularity = float(row.get("p03797_f009", 0))
        change_rate = float(row.get("p03797_f010", 0))
        records.append(ConceptPopularity(
            concept_name=str(row.get("p03797_f001", "")),
            trade_date=normalize_date_display(date_ymd),
            popularity=popularity,
            popularity_change_rate=change_rate,
        ))
    print(f"  获取 {len(records)} 个概念板块")
    return records


def fetch_board_stocks(
    client: IfindClient,
    date_ymd: str,
    concepts: list[str],
    top_n: int = 30,
) -> list[BoardStock]:
    """获取每个概念的成分股，按涨跌幅取 Top N 作为观察股池.

    Args:
        client: ifind API 客户端.
        date_ymd: 交易日期，格式 YYYYMMDD.
        concepts: 概念板块名称列表.
        top_n: 每个板块取涨跌幅前 N 只股票（默认 30）.

    Returns:
        BoardStock 数据类列表.
    """
    print(f"\n[2/4] 获取板块成分股 (p03798), 每板块 Top{top_n}")
    all_records = []
    for i, name in enumerate(concepts):
        print(f"  [{i+1}/{len(concepts)}] {name}...", end=" ")
        try:
            rows = client.get_board_stocks(date_ymd, name)
        except RuntimeError as e:
            print(f"失败: {e}")
            continue
        # 按涨跌幅降序排序，取 Top N，剔除 ST 股
        stocks = []
        for row in rows:
            stock_name = str(row.get("jydm_mc", ""))
            if "ST" in stock_name.upper():
                continue
            stocks.append(BoardStock(
                stock_code=str(row.get("jydm", "")),
                stock_name=stock_name,
                trade_date=normalize_date_display(date_ymd),
                change_ratio=float(row.get("p03798_f012", 0)),
                period_start=str(row.get("p03798_f016", "")),
                concept_name=name,
            ))
        stocks.sort(
            key=lambda s: s.change_ratio, reverse=True,
        )
        top_stocks = stocks[:top_n]
        all_records.extend(top_stocks)
        print(
            f"共 {len(rows)} 只，"
            f"剔除ST后 {len(stocks)} 只，"
            f"取 Top{top_n}: {len(top_stocks)} 只"
        )
        time.sleep(0.1)
    print(f"  共获取 {len(all_records)} 条成分股记录")
    return all_records


def fetch_daily_klines(
    client: IfindClient,
    stock_codes: list[str],
    date_display: str,
) -> list[DailyKline]:
    """批量获取成分股的日K线数据."""
    print(f"\n[3/4] 获取日K线 (cmd_history_quotation)")
    # 获取近5个交易日的数据
    end_dt = datetime.strptime(date_display, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=10)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = date_display

    all_records = []
    batch_size = 50
    total = len(stock_codes)
    for i in range(0, total, batch_size):
        batch = stock_codes[i:i + batch_size]
        batch_num = i // batch_size + 1
        batch_total = (total + batch_size - 1) // batch_size
        print(
            f"  批次 {batch_num}/{batch_total}: "
            f"{len(batch)} 只股票...",
            end=" ",
        )
        try:
            body = client.get_history_quotation(
                codes=batch,
                indicators=[
                    "open", "close", "high",
                    "low", "volume", "amount",
                ],
                startdate=start_date,
                enddate=end_date,
                interval="D",
            )
            tables = body.get("tables", [])
            for tbl_entry in tables:
                if not isinstance(tbl_entry, dict):
                    continue
                code = tbl_entry.get("thscode", "")
                times = tbl_entry.get("time", [])
                table = tbl_entry.get("table", {})
                if not table:
                    continue
                col_names = list(table.keys())
                col_values = [table[k] for k in col_names]
                n = len(col_values[0]) if col_values else 0
                for j in range(n):
                    row = {
                        col_names[k]: col_values[k][j]
                        for k in range(len(col_names))
                    }
                    trade_date = (
                        times[j] if j < len(times) else ""
                    )
                    if not trade_date:
                        continue
                    all_records.append(DailyKline(
                        stock_code=code,
                        trade_date=trade_date,
                        open=float(row.get("open") or 0),
                        high=float(row.get("high") or 0),
                        low=float(row.get("low") or 0),
                        close=float(row.get("close") or 0),
                        volume=float(row.get("volume") or 0),
                        amount=float(row.get("amount") or 0),
                    ))
            print(f"成功")
        except RuntimeError as e:
            print(f"失败: {e}")
        time.sleep(0.1)

    print(f"  共获取 {len(all_records)} 条日K线记录")
    return all_records


def fetch_1min_klines(
    client: IfindClient,
    stock_codes: list[str],
    date_display: str,
) -> list[KlineBar]:
    """批量获取成分股的1分钟K线数据（09:30~09:35）."""
    print(f"\n[4/4] 获取1分钟K线 (high_frequency 09:30~09:35)")
    starttime = f"{date_display} 09:30:00"
    endtime = f"{date_display} 09:35:00"

    all_records = []
    batch_size = 50
    total = len(stock_codes)
    for i in range(0, total, batch_size):
        batch = stock_codes[i:i + batch_size]
        batch_num = i // batch_size + 1
        batch_total = (total + batch_size - 1) // batch_size
        print(
            f"  批次 {batch_num}/{batch_total}: "
            f"{len(batch)} 只股票...",
            end=" ",
        )
        try:
            body = client.get_high_frequency(
                codes=batch,
                indicators=[
                    "open", "high", "low", "close",
                    "volume", "amount",
                    "changeRatio", "LB",
                ],
                starttime=starttime,
                endtime=endtime,
                interval="1",
                calculate={"LB": "5"},
            )
            tables = body.get("tables", [])
            for tbl_entry in tables:
                if not isinstance(tbl_entry, dict):
                    continue
                code = tbl_entry.get("thscode", "")
                times = tbl_entry.get("time", [])
                table = tbl_entry.get("table", {})
                if not table:
                    continue
                col_names = list(table.keys())
                col_values = [table[k] for k in col_names]
                n = len(col_values[0]) if col_values else 0
                for j in range(n):
                    row = {
                        col_names[k]: col_values[k][j]
                        for k in range(len(col_names))
                    }
                    bar_time = (
                        times[j] if j < len(times) else ""
                    )
                    change_ratio = row.get("changeRatio")
                    all_records.append(KlineBar(
                        stock_code=code,
                        trade_date=date_display,
                        bar_time=bar_time,
                        open=float(row.get("open") or 0),
                        high=float(row.get("high") or 0),
                        low=float(row.get("low") or 0),
                        close=float(row.get("close") or 0),
                        volume=float(row.get("volume") or 0),
                        amount=float(row.get("amount") or 0),
                        change_ratio=(
                            float(change_ratio)
                            if change_ratio is not None
                            else None
                        ),
                    ))
            print(f"成功")
        except RuntimeError as e:
            print(f"失败: {e}")
        time.sleep(0.1)

    print(f"  共获取 {len(all_records)} 条1分钟K线记录")
    return all_records


def main() -> None:
    """执行数据采集主流程."""
    # 加载环境变量
    load_env(project_root / ".env")

    # 解析日期参数
    today_str = sys.argv[1] if len(sys.argv) > 1 else (
        datetime.now().strftime("%Y%m%d")
    )
    date_ymd = parse_date(today_str)
    date_display = normalize_date_display(date_ymd)
    print(f"采集日期: {date_display}")

    # 初始化配置和客户端
    config = get_config()
    client = IfindClient(
        base_url=config.ifind_base_url,
        refresh_token=config.ifind_refresh_token,
    )

    # 初始化数据库
    db = Database(config.db_path)
    db.init_db()

    # 1. 获取概念人气排名
    concepts = fetch_concept_popularity(client, date_ymd)
    db.upsert_concept_popularity(concepts)

    # 按 spec 筛选热门概念板块：热度 Top20 + 变化率 Top20，合并去重
    by_popularity = sorted(
        concepts, key=lambda c: c.popularity, reverse=True,
    )[:20]
    by_change = sorted(
        concepts, key=lambda c: c.popularity_change_rate,
        reverse=True,
    )[:20]
    seen = set()
    hot_concepts = []
    for c in by_popularity + by_change:
        if c.concept_name not in seen:
            seen.add(c.concept_name)
            hot_concepts.append(c)
    print(
        f"\n热门概念板块: {len(hot_concepts)} 个 "
        f"(热度Top20 + 变化率Top20 去重)"
    )

    # 2. 获取每个板块涨幅 Top30 成分股
    top_per_board = int(
        sys.argv[2]
    ) if len(sys.argv) > 2 else 30
    board_stocks = fetch_board_stocks(
        client, date_ymd,
        [c.concept_name for c in hot_concepts],
        top_per_board,
    )
    db.upsert_board_stocks(board_stocks)

    # 去重获取所有成分股代码
    stock_codes = list({
        bs.stock_code for bs in board_stocks
    })
    print(f"\n去重后共 {len(stock_codes)} 只股票")

    # 3. 获取日K线
    daily_klines = fetch_daily_klines(
        client, stock_codes, date_display
    )
    db.upsert_daily_klines(daily_klines)

    # 4. 获取1分钟K线
    kline_1min = fetch_1min_klines(
        client, stock_codes, date_display
    )
    db.upsert_kline_1min(kline_1min)

    db.close()

    # 汇总
    print(f"\n{'='*60}")
    print(f"数据采集完成: {date_display}")
    print(f"  概念板块: {len(concepts)} 个")
    print(f"  成分股: {len(board_stocks)} 条 "
          f"({len(stock_codes)} 只去重)")
    print(f"  日K线: {len(daily_klines)} 条")
    print(f"  1分钟K线: {len(kline_1min)} 条")
    print(f"  数据库: {config.db_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
