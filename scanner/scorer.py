"""多因子综合评分引擎.

提供 ``ScoringEngine`` 类，基于涨幅、实体涨幅、成交额、
量比四个因子对观察股池中的个股进行强势评分，并聚合计算
概念板块评分。
"""

from __future__ import annotations

import logging

from scanner.db import Database

logger = logging.getLogger(__name__)


class ScoringEngine:
    """多因子综合评分引擎.

    从 SQLite 读取 K 线和关联数据，计算个股/板块强势
    得分并写入扫描结果表.

    Attributes:
        db: 数据库管理器实例.
        weights: 四个因子的权重字典.
        strong_change_threshold: 涨幅强势阈值(%).
        strong_body_threshold: 实体涨幅强势阈值(%).
        board_weights: 板块评分中强势占比和均分的权重.
    """

    def __init__(
        self,
        db: Database,
        scoring_config: dict,
        board_config: dict,
    ) -> None:
        """初始化评分引擎.

        Args:
            db: 数据库管理器实例.
            scoring_config: 评分权重和阈值配置.
            board_config: 板块评分权重配置.
        """
        self.db = db
        self.weights = {
            "change_ratio": scoring_config.get(
                "weight_change_ratio", 0.25
            ),
            "body_change": scoring_config.get(
                "weight_body_change", 0.30
            ),
            "amount": scoring_config.get(
                "weight_amount", 0.20
            ),
            "vol_ratio": scoring_config.get(
                "weight_vol_ratio", 0.25
            ),
        }
        self.strong_change_threshold = scoring_config.get(
            "strong_change_threshold", 7.0
        )
        self.strong_body_threshold = scoring_config.get(
            "strong_body_threshold", 5.0
        )
        self.board_weights = {
            "strong_ratio": board_config.get(
                "strong_ratio_weight", 0.6
            ),
            "avg_score": board_config.get(
                "avg_score_weight", 0.4
            ),
        }

    def run(
        self, trade_date: str
    ) -> tuple[list[dict], list[dict]]:
        """执行完整评分流程并写入数据库.

        Args:
            trade_date: 交易日期字符串.

        Returns:
            (stock_results, board_results) 元组.
        """
        pool = self.db.get_monitor_pool(trade_date)
        if not pool:
            logger.warning(
                "No monitor pool for %s.", trade_date
            )
            return [], []

        stock_codes = [code for code, _ in pool]
        stock_names = {c: n for c, n in pool}
        logger.info(
            "Scoring %d stocks for %s.",
            len(stock_codes), trade_date,
        )

        prev_closes = self.db.get_prev_close(
            stock_codes, trade_date
        )
        klines = self.db.get_kline_1min_batch(
            trade_date, stock_codes
        )
        stock_concepts = self.db.get_stock_concepts(
            trade_date
        )

        stock_results = self._score_stocks(
            trade_date, stock_codes, stock_names,
            prev_closes, klines, stock_concepts,
        )
        board_results = self._score_boards(
            trade_date, stock_results, stock_concepts,
        )

        self.db.save_stock_scan_results(
            trade_date, stock_results
        )
        self.db.save_board_scan_results(
            trade_date, board_results
        )

        logger.info(
            "Scored %d stocks, %d boards for %s.",
            len(stock_results), len(board_results),
            trade_date,
        )
        return stock_results, board_results

    # ------------------------------------------------------------------
    # 个股评分
    # ------------------------------------------------------------------

    def _score_stocks(
        self,
        trade_date: str,
        stock_codes: list[str],
        stock_names: dict[str, str],
        prev_closes: dict[str, float],
        klines: dict[str, list[dict]],
        stock_concepts: dict[str, list[str]],
    ) -> list[dict]:
        """计算所有个股的因子和综合评分.

        Args:
            trade_date: 交易日期.
            stock_codes: 股票代码列表.
            stock_names: 代码 -> 名称映射.
            prev_closes: 代码 -> 昨收价映射.
            klines: 代码 -> 1min K 线列表映射.
            stock_concepts: 代码 -> 概念名称列表映射.

        Returns:
            评分结果字典列表.
        """
        raw_factors: list[dict] = []
        skipped = 0

        for code in stock_codes:
            prev_close = prev_closes.get(code)
            bars = klines.get(code, [])
            if prev_close is None or not bars:
                skipped += 1
                continue

            factors = self._calc_stock_factors(
                code, bars, prev_close
            )
            if factors is None:
                skipped += 1
                continue

            concepts = stock_concepts.get(code, [])
            factors["stock_code"] = code
            factors["stock_name"] = stock_names.get(
                code, ""
            )
            factors["concept_names"] = ",".join(concepts)
            factors["pre_close"] = prev_close
            raw_factors.append(factors)

        if skipped:
            logger.info(
                "Skipped %d stocks (no data).", skipped
            )

        if not raw_factors:
            return []

        # 归一化每个因子到 0-100
        self._normalize_field(
            raw_factors, "change_ratio"
        )
        self._normalize_field(
            raw_factors, "body_change_ratio"
        )
        self._normalize_field(
            raw_factors, "total_amount"
        )
        self._normalize_field(
            raw_factors, "vol_ratio"
        )

        # 加权评分 + 强势标记
        results = []
        for f in raw_factors:
            score = (
                f["change_ratio_norm"] * self.weights[
                    "change_ratio"
                ]
                + f["body_change_ratio_norm"]
                * self.weights["body_change"]
                + f["total_amount_norm"] * self.weights[
                    "amount"
                ]
                + f["vol_ratio_norm"] * self.weights[
                    "vol_ratio"
                ]
            )
            results.append({
                "stock_code": f["stock_code"],
                "stock_name": f["stock_name"],
                "concept_names": f["concept_names"],
                "pre_close": f["pre_close"],
                "open_price": f["open_price"],
                "current_price": f["current_price"],
                "change_ratio": round(
                    f["change_ratio"], 4
                ),
                "body_change_ratio": round(
                    f["body_change_ratio"], 4
                ),
                "total_amount": round(
                    f["total_amount"], 2
                ),
                "total_volume": round(
                    f["total_volume"], 2
                ),
                "vol_ratio": round(
                    f["vol_ratio"], 4
                ),
                "score": round(score, 2),
            })

        results.sort(
            key=lambda r: r["score"], reverse=True
        )
        return results

    def _calc_stock_factors(
        self,
        stock_code: str,
        bars: list[dict],
        prev_close: float,
    ) -> dict | None:
        """计算单只股票的原始因子值.

        仅使用前 2 根 1 分钟 K 线（09:30、09:31）
        进行计算。

        Args:
            stock_code: 股票代码.
            bars: 1 分钟 K 线字典列表（按时间升序）.
            prev_close: 前一交易日收盘价.

        Returns:
            包含所有原始因子值的字典，或 None 表示数据
            不足以计算.
        """
        used_bars = bars[:2]
        if len(used_bars) < 2:
            return None

        first_open = used_bars[0]["open"]
        last_close = used_bars[-1]["close"]

        if prev_close <= 0 or first_open <= 0:
            return None

        change_ratio = (
            (last_close - prev_close) / prev_close * 100
        )
        body_change_ratio = (
            (last_close - first_open) / first_open * 100
        )
        total_amount = sum(
            b.get("amount") or 0 for b in used_bars
        )
        total_volume = sum(
            b.get("volume") or 0 for b in used_bars
        )
        vol_ratio = 0.0

        return {
            "open_price": first_open,
            "current_price": last_close,
            "change_ratio": change_ratio,
            "body_change_ratio": body_change_ratio,
            "total_amount": total_amount,
            "total_volume": total_volume,
            "vol_ratio": vol_ratio,
        }

    @staticmethod
    def _normalize_field(
        items: list[dict],
        field: str,
    ) -> None:
        """对列表中每个字典的指定字段做百分位归一化.

        将 *field* 的值归一化为 0-100 并存入
        ``{field}_norm`` 键。值为 0 的项（如缺失量比）
        被赋予中位数 50.

        Args:
            items: 因子字典列表.
            field: 要归一化的字段名.
        """
        values = [item[field] for item in items]
        n = len(values)
        if n <= 1:
            for item in items:
                item[f"{field}_norm"] = 50.0
            return

        sorted_pairs = sorted(
            enumerate(values), key=lambda p: p[1]
        )
        norm_values = [0.0] * n
        for rank, (idx, val) in enumerate(sorted_pairs):
            if val == 0.0:
                norm_values[idx] = 50.0
            else:
                norm_values[idx] = (
                    rank / (n - 1) * 100
                )

        for i, item in enumerate(items):
            item[f"{field}_norm"] = norm_values[i]

    # ------------------------------------------------------------------
    # 板块评分
    # ------------------------------------------------------------------

    def _score_boards(
        self,
        trade_date: str,
        stock_results: list[dict],
        stock_concepts: dict[str, list[str]],
    ) -> list[dict]:
        """计算概念板块评分.

        从已排序的 stock_results 取 Top 50 个股作为强势
        个股池，统计每个板块在 Top 50 中的数量与得分，计算
        板块评分。

        board_score = top50_count × 10 + top50_avg_score × 0.5

        Args:
            trade_date: 交易日期.
            stock_results: 个股评分结果列表（已按 score 降序）.
            stock_concepts: 代码 -> 概念名称列表映射.

        Returns:
            板块评分结果字典列表（已按 board_score 降序）.
        """
        # 1. 取 Top 50 强势个股
        top50 = stock_results[:50]

        # 2. 构建每只股票所属板块列表（从 concept_names 字段）
        stock_concept_map: dict[str, list[str]] = {}
        for r in stock_results:
            names = r.get("concept_names", "")
            if names:
                stock_concept_map[r["stock_code"]] = (
                    names.split(",")
                )
            else:
                stock_concept_map[r["stock_code"]] = []

        # 3. 构建板块 -> 全部成分股 映射
        stock_map = {
            r["stock_code"]: r for r in stock_results
        }
        board_all_stocks: dict[str, list[dict]] = {}
        for code, concepts in stock_concept_map.items():
            if code not in stock_map:
                continue
            for concept in concepts:
                board_all_stocks.setdefault(
                    concept, []
                ).append(stock_map[code])

        # 4. 构建板块 -> Top50 成分股 映射
        board_top50: dict[str, list[dict]] = {}
        for r in top50:
            for concept in stock_concept_map.get(
                r["stock_code"], []
            ):
                board_top50.setdefault(
                    concept, []
                ).append(r)

        # 5. 计算每个板块的指标和评分
        results = []
        for concept in board_top50:
            top50_stocks = board_top50[concept]
            top50_count = len(top50_stocks)
            if top50_count == 0:
                continue

            top50_avg_score = (
                sum(s["score"] for s in top50_stocks)
                / top50_count
            )
            top50_avg_change = (
                sum(
                    s["change_ratio"]
                    for s in top50_stocks
                )
                / top50_count
            )

            all_stocks = board_all_stocks.get(concept, [])
            stock_count = len(all_stocks)
            board_avg_change = (
                sum(
                    s["change_ratio"]
                    for s in all_stocks
                )
                / stock_count
                if stock_count > 0
                else 0.0
            )

            board_score = (
                top50_count * 10 + top50_avg_score * 0.5
            )

            results.append({
                "concept_name": concept,
                "stock_count": stock_count,
                "top50_count": top50_count,
                "top50_avg_score": round(
                    top50_avg_score, 2
                ),
                "top50_avg_change": round(
                    top50_avg_change, 4
                ),
                "board_avg_change": round(
                    board_avg_change, 4
                ),
                "board_score": round(board_score, 2),
            })

        results.sort(
            key=lambda r: r["board_score"], reverse=True
        )
        return results
