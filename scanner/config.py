"""概念板块强势扫描系统配置加载模块.

从项目根目录的 config.yaml 读取配置，并从环境变量
IFIND_REFRESH_TOKEN 获取 ifind 鉴权令牌。
通过 ``get_config()`` 获取全局单例配置实例。
"""

import os
from pathlib import Path

import yaml


class Config:
    """基于 config.yaml 和环境变量的应用配置.

    Attributes:
        ifind_base_url: ifind 量化 API 基础地址.
        ifind_refresh_token: 从环境变量 IFIND_REFRESH_TOKEN
            读取的鉴权令牌.
        scoring: 评分权重参数.
        board_scoring: 板块级评分参数.
        scheduler: 调度器时间参数.
        database: 数据库路径配置.
        webhook: Webhook 地址配置.
    """

    def __init__(self, data: dict) -> None:
        """从解析后的 YAML 字典初始化配置.

        Args:
            data: config.yaml 解析后的字典.
        """
        ifind = data.get("ifind", {})
        self.ifind_base_url: str = ifind.get(
            "base_url", "https://quantapi.51ifind.com"
        )
        self.ifind_refresh_token: str = os.getenv(
            "IFIND_REFRESH_TOKEN", ""
        )

        self.scoring: dict = data.get("scoring", {})
        self.board_scoring: dict = data.get("board_scoring", {})
        self.scheduler: dict = data.get("scheduler", {})
        self.database: dict = data.get("database", {})
        self.webhook: dict = data.get("webhook", {})

    @property
    def db_path(self) -> Path:
        """返回解析后的数据库文件路径."""
        raw: str = self.database.get("path", "data/scanner.db")
        return Path(raw)


_config: Config | None = None


def get_config(config_path: str | None = None) -> Config:
    """返回全局单例 Config 实例.

    首次调用时读取并解析 YAML 文件，后续调用直接返回
    缓存实例，忽略 *config_path* 参数。

    Args:
        config_path: 可选的 config.yaml 路径，默认为项目
            根目录下的 ``config/config.yaml``.

    Returns:
        全局 Config 实例.
    """
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        project_root = Path(__file__).resolve().parent.parent
        config_path = str(project_root / "config" / "config.yaml")

    with open(config_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    _config = Config(data)
    return _config
