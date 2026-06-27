# cutout.py — 批量商品抠图工具

## 用途

把 `raw_images/` 里的 30 张商品原图（带背景）批量抠成透明底 PNG，输出到 `frontend/assets/items/`。

## 用法

```bash
cd fashionmix-studio
pip install -r backend/requirements.txt  # 一次性安装 rembg + Pillow

# 准备原图
mkdir -p raw_images
# 把 30 张原图拷到 raw_images/，文件名无所谓，脚本按字母序处理

# 批量抠图
python tools/cutout.py --input ./raw_images --output ./frontend/assets/items
```

## 第一次运行

rembg 会自动下载 u2netp 模型到 `~/.u2net/`（约 170MB）。之后不再下载。

## 命名规则

输出文件：`item_001.png`, `item_002.png`, ... `item_030.png`。

> ⚠️ products.json 里的 `image` 字段已经硬编码为 `assets/items/<id>.png`（如 `assets/items/skirt_001.png`），但 cutout.py 默认输出 `item_NNN.png` 格式。
> 你需要**二选一**：
> 1. 改 products.json 的 `image` 字段为 `assets/items/item_NNN.png`
> 2. 或者让 cutout.py 按 ID 命名（见 `cutout.py --prefix` 选项）
>
> 建议：保持当前架构。让 cutout.py 输出 `item_NNN.png`，然后 products.json 用映射表
> `id -> item_NNN.png` 关联。最简单做法是：把 30 个商品按你截屏里看到的顺序放进 raw_images/，
> 截屏里的"第一件"=item_001.png，"第二件"=item_002.png，以此类推。
> 然后把 products.json 的 `image` 字段批量改为 `assets/items/item_NNN.png`（用 Task 2 里的脚手架脚本做）。