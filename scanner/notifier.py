"""企业微信 Webhook 推送模块.

提供 ``Notifier`` 类，将扫描结果格式化为 Markdown
报告并通过企业微信群机器人 Webhook 推送。报告采用
两段式结构：Top 10 个股归类 + Top 5 板块详情。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# 企业微信 Markdown 消息字节上限.
_MAX_BYTES = 4096


class Notifier:
    """企业微信 Webhook 推送器.

    Attributes:
        webhook_url: Webhook 地址.
    """

    def __init__(self, webhook_url: str) -> None:
        """初始化推送器.

        Args:
            webhook_url: 企业微信群机器人 Webhook URL.
        """
        self.webhook_url = webhook_url

    def send(
        self,
        trade_date: str,
        stock_results: list[dict],
        board_results: list[dict],
    ) -> bool:
        """格式化并推送扫描报告.

        Args:
            trade_date: 交易日期（YYYY-MM-DD）.
            stock_results: 个股评分结果列表.
            board_results: 板块评分结果列表.

        Returns:
            推送是否成功.
        """
        if not self.webhook_url:
            logger.warning(
                "Webhook URL not configured, skip push."
            )
            return False

        content = self._build_report(
            trade_date, stock_results, board_results,
        )
        if not content:
            logger.warning(
                "Empty report, skip push for %s.",
                trade_date,
            )
            return False

        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_BYTES:
            logger.warning(
                "Report too large (%d bytes), truncating.",
                len(encoded),
            )
            content = encoded[:_MAX_BYTES].decode(
                "utf-8", errors="ignore",
            )

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode", 0) != 0:
                logger.error(
                    "Webhook returned error: %s",
                    data.get("errmsg", "unknown"),
                )
                return False
            logger.info(
                "Push succeeded for %s.", trade_date,
            )
            return True
        except requests.RequestException as exc:
            logger.error(
                "Webhook push failed for %s: %s",
                trade_date, exc,
            )
            return False

    # ------------------------------------------------------------------
    # 报告构建
    # ------------------------------------------------------------------

    def _build_report(
        self,
        trade_date: str,
        stock_results: list[dict],
        board_results: list[dict],
    ) -> str:
        """构建两段式 Markdown 报告.

        Args:
            trade_date: 交易日期.
            stock_results: 个股评分列表.
            board_results: 板块评分列表.

        Returns:
            Markdown 格式报告字符串.
        """
        now = datetime.now().strftime("%H:%M")
        pool_count = len(stock_results)
        strong_count = sum(
            1 for s in stock_results if s.get("is_strong")
        )

        lines: list[str] = [
            f"### 概念板块强势扫描 {trade_date}",
            f"> 扫描时间：{now} | "
            f"观察股池：{pool_count}只 | "
            f"强势个股：{strong_count}只",
        ]

        # 个股归属板块
        board_score_map = {
            b["concept_name"]: b["board_score"]
            for b in board_results
        }
        for s in stock_results:
            concepts = (
                s.get("concept_names", "").split(",")
            )
            s["_best_concept"] = max(
                concepts,
                key=lambda c: board_score_map.get(c, 0),
                default="",
            )

        # 第一段：Top 10 个股归类
        lines.append("")
        lines.append("**Top 10 强势个股（按板块归类）**")
        top_10 = sorted(
            stock_results,
            key=lambda s: s.get("score", 0),
            reverse=True,
        )[:10]

        # 按板块分组
        grouped: dict[str, list[tuple[int, dict]]] = {}
        for idx, stock in enumerate(top_10, 1):
            concept = stock.get("_best_concept", "")
            grouped.setdefault(concept, []).append(
                (idx, stock)
            )

        # 板块按 board_score 降序
        sorted_groups = sorted(
            grouped.items(),
            key=lambda g: board_score_map.get(g[0], 0),
            reverse=True,
        )

        for concept, items in sorted_groups:
            bs = board_score_map.get(concept, 0)
            name = _truncate(concept, 12)
            lines.append("")
            lines.append(f"▎{name} — 板块得分 {bs:.2f}")
            for rank, stock in items:
                lines.append(
                    f"  {rank}. "
                    + _format_stock_line(stock)
                )

        # 第二段：Top 5 板块详情
        lines.append("")
        lines.append("**Top 5 强势板块**")
        top_5_boards = sorted(
            board_results,
            key=lambda b: b.get("board_score", 0),
            reverse=True,
        )[:5]

        for brd_rank, board in enumerate(top_5_boards, 1):
            concept = board["concept_name"]
            bs = board["board_score"]
            sc = board.get("strong_count", 0)
            tc = board.get("stock_count", 0)
            name = _truncate(concept, 12)
            lines.append("")
            lines.append(
                f"▎{brd_rank}. {name} | "
                f"得分 {bs:.2f} | 强势 {sc}/{tc}"
            )
            board_stocks = sorted(
                [
                    s for s in stock_results
                    if s.get("_best_concept") == concept
                ],
                key=lambda s: s.get("score", 0),
                reverse=True,
            )[:5]
            for s_rank, stock in enumerate(board_stocks, 1):
                lines.append(
                    f"  {s_rank}. "
                    + _format_stock_line(stock)
                )

        return "\n".join(lines)


def _format_stock_line(stock: dict) -> str:
    """格式化单只个股行.

    Args:
        stock: 个股评分字典.

    Returns:
        格式化后的字符串.
    """
    name = stock.get("stock_name", "")
    code = stock.get("stock_code", "").split(".")[0]
    score = stock.get("score", 0)
    change = stock.get("change_ratio", 0)
    body = stock.get("body_change_ratio", 0)
    amount = stock.get("total_amount", 0)
    is_strong = stock.get("is_strong")

    name_str = (
        f"**{name}({code})**"
        if is_strong else f"{name}({code})"
    )
    change_str = _fmt_pct(change)
    body_str = _fmt_pct(body)
    amount_str = _fmt_amount(amount)

    return (
        f"{name_str} 得分{score:.2f} | "
        f"涨{change_str} | 实{body_str} | {amount_str}"
    )


def _fmt_pct(value: float) -> str:
    """格式化百分比值，正数加 + 号."""
    if value > 0:
        return f"+{value:.2f}%"
    return f"{value:.2f}%"


def _fmt_amount(value: float) -> str:
    """格式化成交额."""
    if value >= 1e8:
        return f"{value / 1e8:.2f}亿"
    if value >= 1e4:
        return f"{value / 1e4:.0f}万"
    return f"{value:.0f}元"


def _truncate(text: str, max_len: int) -> str:
    """截断文本到指定长度."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
