# FashionMix Studio V0.2

低预算风格搭配模拟器：把便宜单品变成可视化穿搭方案。

## 快速开始

### 一键启动 (推荐)

**Windows:**
```cmd
scripts\start-dev.bat
```

**Git Bash / Linux / Mac:**
```bash
bash scripts/start-dev.sh
```

### 手动启动

**后端:**
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# 编辑 .env 填入 GEMINI_API_KEY
uvicorn app:app --port 8001 --reload
```

**前端 (另开终端，从项目根目录 serve):**
```bash
cd fashionmix-studio    # 注意：必须从项目根 serve，不要 -d frontend
python -m http.server 8000
```

打开 **http://localhost:8000/** （根路径会自动跳转到 `frontend/index.html`）

> ⚠️ **不要用** `python -m http.server 8000 -d frontend`——这会阻止 `data/products.json` 路径解析。

## 测试

```bash
# 后端
cd fashionmix-studio
python -m pytest tests/ -v

# 前端
node --test frontend/lib/*.test.js
```

## 抠图工具

```bash
mkdir raw_images
# 放入 30 张原图
python tools/cutout.py --input ./raw_images --output ./frontend/assets/items
```

详见 [`tools/README.md`](tools/README.md)。

## 文档

- 设计 spec: `../docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md`
- 实现计划: `../docs/superpowers/plans/2026-06-27-fashionmix-studio-v02.md`
- 截图指南: `tools/README.md`