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
>
> **方案 A（推荐）：一次跑完，重命名 products.json**
> 1. 把 30 张原图按任意顺序放进 `raw_images/`
> 2. 跑：`python tools/cutout.py --input ./raw_images --output ./frontend/assets/items`
> 3. 生成 `item_001.png` ~ `item_030.png`
> 4. 重命名 `frontend/assets/items/item_001.png` → `skirt_001.png`、`item_002.png` → `skirt_002.png`... 等等，按你想要的映射
> 5. 或更简单：把 products.json 的所有 `image` 字段从 `assets/items/<id>.png` 改为 `assets/items/item_NNN.png`（按 inventory 顺序）
>
> **方案 B：按类别分批跑**
> 1. 把 6 张裙子图放 `raw_images/skirts/`、6 张上衣图放 `raw_images/tops/`...
> 2. 每批用不同 `--prefix`：
>    ```bash
>    python tools/cutout.py --input raw_images/skirts --output frontend/assets/items --prefix skirt_ --start 1
>    python tools/cutout.py --input raw_images/tops   --output frontend/assets/items --prefix top_   --start 1
>    # ... 其他 4 类同理
>    ```
> 3. **必须用 `--start 1` 防止后续批次覆盖之前的（每类都是从头编号）**
>
> 方案 A 更简单，方案 B 更贴合 products.json 的命名但要管 6 个文件夹。