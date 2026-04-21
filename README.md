# Prompta — Your Prompt Workspace

## 核心特性

- 提示词资产管理： 集中管理 Prompt，让提示词从零散文本变为可复用资产
- Prompt 模板化： 支持变量化 Prompt（{{variable}}），通过表单填写参数即可复用，提升 Prompt 的通用性与效率
- Prompt 运行与模型调用： 选择 Prompt 并直接调用 LLM 执行，支持多模型接入

## 快速开始

1. 克隆代码

```shell
git clone https://github.com/ChamfersChen/prompta.git
cd prompta
```

2. 创建后端环境
```shell
uv init
uv sync
# MAC/Linux
source ./.venv/activate
# Windows
.\.venv\Scripts\activate.bat
```

3. 运行后端
```shell
uv run --no-dev uvicorn server.main:app --host 0.0.0.0 --port 15050
```

4. 创建前端环境
```shell
cd web
npm install -g pnpm@latest
pnpm install --frozen-lockfile --registry=https://registry.npmmirror.com
```

5. 运行前端
```shell
pnpm run dev
```

6. 访问页面
等待启动完成后，访问 http://localhost:15173

## API Key 调用 Prompt
1. `我的 - 系统设置 - API Key` 创建API Key
2. `Get请求`: ip:15050/api/open/prompts/{external}
    注意：`external`值从'提示词管理'界面选中文件进行复制
3. `Header`: x-api-key: {API Key}

