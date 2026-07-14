"""全局测试基线（V0.5）。

api_keys 表非空（含已吊销记录）会让服务进入认证模式——这是商用保护设计。
测试共享项目 data/ 下的 SQLite，上一次运行残留的 key 会把所有开放模式
测试变成 401，因此每个测试开始前统一清空 api_keys 表。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _open_mode_baseline():
    from backend import database as db
    from backend.billing import purge_keys

    db.init_db()
    purge_keys()
    yield
