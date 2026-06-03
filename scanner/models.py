"""概念板块和个股数据模型.

定义用于结构化表示概念人气、板块成分股、
分钟 K 线及日 K 线数据的数据类。
"""

from dataclasses import dataclass


@dataclass
class ConceptPopularity:
    """概念人气明细.

    Attributes:
        concept_name: 概念板块名称 (p03797_f001).
        trade_date: 交易日期 (p03797_f002).
        popularity: 人气值 (p03797_f009).
        popularity_change_rate: 人气变化率 (p03797_f010).
    """

    concept_name: str
    trade_date: str
    popularity: float
    popularity_change_rate: float


@dataclass
class BoardStock:
    """板块热门成分股.

    Attributes:
        stock_code: 交易代码 (jydm).
        stock_name: 证券名称 (jydm_mc).
        trade_date: 交易日期 (p03798_f001).
        change_ratio: 涨跌幅 (p03798_f012).
        period_start: 统计周期起始 (p03798_f016).
        concept_name: 所属概念名称（来自请求参数）.
    """

    stock_code: str
    stock_name: str
    trade_date: str
    change_ratio: float
    period_start: str
    concept_name: str


@dataclass
class KlineBar:
    """K 线单根数据（1分钟 bar）.

    Attributes:
        stock_code: 证券代码.
        trade_date: 交易日期.
        bar_time: bar 时间.
        open: 开盘价.
        high: 最高价.
        low: 最低价.
        close: 收盘价.
        volume: 成交量.
        amount: 成交额.
        change_ratio: 涨跌幅，可能为 None.
    """

    stock_code: str
    trade_date: str
    bar_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    change_ratio: float | None


@dataclass
class DailyKline:
    """日 K 线数据.

    Attributes:
        stock_code: 证券代码.
        trade_date: 交易日期.
        open: 开盘价.
        high: 最高价.
        low: 最低价.
        close: 收盘价.
        volume: 成交量.
        amount: 成交额.
    """

    stock_code: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
