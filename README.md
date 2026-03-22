# PDF 标注工具

一个本地运行的 PDF 标注工具，用于把论文或文档内容标注为结构化 JSON。项目包含纯前端标注界面和一个本地 PaddleOCR 后端，`git clone` 后按 README 安装依赖即可直接启动。

## 功能概览

- 浏览 PDF 并框选证据区域
- 按 JSON Schema 层级选择标注字段
- 支持数组字段索引切换与新增
- 支持上传 `json_schema.json` 动态生成字段树
- 支持上传 `json_schema.jsonc` / 注释版 schema 作为辅助说明
- 框选后自动调用本地 OCR 回填文本
- 不框选也可以直接手动输入并保存标注
- 实时查看“当前 JSON 结果”
- 导出当前界面中“查看 JSON”的最终结果
- 导出截图

## 项目结构

```text
.
├── backend/
│   ├── paddle_ocr_server.py
│   └── 启动说明.md
├── frontend/
│   ├── index.html
│   └── 教学文档.md
├── requirements.txt
├── start_app.sh
├── paper_schema.json
├── paper_schema.jsonc
└── README.md
```

## 环境要求

- Python 3.10 及以上
- macOS / Linux 优先，Windows 建议在 WSL 中运行
- 建议使用虚拟环境

## 依赖说明

当前后端代码实际使用并已核对过的核心依赖如下：

- `fastapi`
- `uvicorn`
- `pydantic`
- `numpy`
- `pillow`
- `paddleocr`
- `paddlepaddle`

安装方式：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

说明：

- `requirements.txt` 已覆盖当前项目运行所需 Python 依赖
- `paddlepaddle` 是安装包名，Python 中实际导入模块名是 `paddle`
- 首次安装 `paddleocr` / `paddlepaddle` 可能较慢
- 第一次真正调用 OCR 时，模型文件可能下载到 `backend/.runtime/`

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd 标注工具
```

### 2. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 启动前后端

在项目根目录执行：

```bash
bash start_app.sh
```

`start_app.sh` 会优先使用 `python3`，如不存在则回退到 `python`。

启动成功后默认地址：

- 前端：`http://127.0.0.1:8080/`
- OCR：`http://127.0.0.1:8765/ocr`
- 健康检查：`http://127.0.0.1:8765/health`

### 4. 验证是否启动成功

浏览器打开前端地址，或在终端执行：

```bash
curl http://127.0.0.1:8765/health
```

正常情况下会返回包含 `"ok": true` 的 JSON。

## 使用流程

1. 启动服务并打开前端页面
2. 上传 PDF 文件
3. 可选上传自己的 `json_schema.json`
4. 可选上传带注释的 `json_schema.jsonc`
5. 选择目标字段
6. 两种标注方式任选一种：
   - 在 PDF 上框选区域，自动 OCR 后保存
   - 不框选，直接手动填写内容并保存
7. 在“查看 JSON”中检查当前结构化结果
8. 点击“导出 JSON”导出当前最终结果

## 单独启动

如果只想单独启动后端：

```bash
python -m uvicorn backend.paddle_ocr_server:app --host 127.0.0.1 --port 8765
```

如果只想启动前端静态服务：

```bash
python -m http.server 8080 --bind 127.0.0.1 --directory frontend
```

## 主要文件

- 前端入口：`frontend/index.html`
- 前端教学文档：`frontend/教学文档.md`
- 后端服务：`backend/paddle_ocr_server.py`
- 后端说明：`backend/启动说明.md`
- 启动脚本：`start_app.sh`
- Python 依赖：`requirements.txt`

## 常见问题

### 1. 为什么安装很慢？

`paddleocr` 和 `paddlepaddle` 体积较大，首次安装和首次 OCR 推理都可能较慢，这是正常现象。

### 2. 为什么前端不能直接双击打开？

前端依赖浏览器中的文件访问与接口请求，建议始终通过 `http.server` 或 `start_app.sh` 启动，不建议直接双击 `html` 文件。

### 3. 端口被占用了怎么办？

可以自定义端口：

```bash
BACKEND_PORT=8865 FRONTEND_PORT=8081 bash start_app.sh
```

### 4. 运行 OCR 失败怎么办？

优先检查以下几点：

- 是否已执行 `python -m pip install -r requirements.txt`
- `http://127.0.0.1:8765/health` 是否可访问
- 首次模型下载是否因网络问题失败

## 补充说明

- `backend/.runtime/` 是本地缓存目录，已在 `.gitignore` 中忽略
- 导出的 JSON 内容与界面“查看 JSON”区域保持一致
- 标注列表中的无框选条目也会正常参与最终 JSON 生成
