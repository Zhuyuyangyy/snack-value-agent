# FashionMix Studio V0.2

低预算风格搭配模拟器：把便宜单品变成可视化穿搭方案。

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
cp ../.env.example .env  # 填入 GEMINI_API_KEY
uvicorn app:app --port 8001 --reload

# 前端 (另开终端)
cd ..
python -m http.server 8000 -d frontend
```

打开 http://localhost:8000

## 文档

- 设计 spec: `../docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md`
- 实现计划: `../docs/superpowers/plans/2026-06-27-fashionmix-studio-v02.md`