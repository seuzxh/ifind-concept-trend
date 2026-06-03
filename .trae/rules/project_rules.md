# 项目规则文档

## 1. 虚拟环境管理

- **环境管理工具**: conda
- **虚拟环境名称**: concept-trend
- **Python 版本**: 3.10

## 2. 环境变量

- **配置文件**: 项目根目录 `.env`（参考 `.env.example`）
- **敏感令牌禁止写入代码或版本控制**
- 必须在项目根目录创建 `.env` 文件，`.env.example` 仅作为模板提交

### 必需环境变量

| 变量名 | 用途 | 来源 |
|--------|------|------|
| `IFIND_REFRESH_TOKEN` | ifind 量化 API 鉴权令牌 | 同花顺量化平台获取 |

### 环境变量使用规范

- 通过 `os.getenv()` 读取环境变量，提供合理的默认值
- 环境变量名使用全大写 + 下划线分隔（如 `IFIND_REFRESH_TOKEN`）
- 新增环境变量时必须同步更新 `.env.example`
- `.env` 文件必须在 `.gitignore` 中（禁止提交敏感信息）
- 配置模板文件为 `config/config.yaml.template`，实际配置为
  `config/config.yaml`（同样禁止提交）
