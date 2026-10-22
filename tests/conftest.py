# conftest.py —— pytest 的 fixtures（每个用例运行前的准备，自动加载）
import os
import sys

# 保证 tests/ 目录在 sys.path，这样用例里 `from api_client import ...` 才找得到
sys.path.insert(0, os.path.dirname(__file__))

import pytest
import requests
from api_client import ApiClient
from helpers import register_user

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture(scope="session", autouse=True)
def reset_db_before_suite():
    """整条套件开始前清空一次数据库 —— 这是 Python 版的「自动化重置」。

    等价于 Apifox 场景「前置操作」里那行 JS 去触发 /api/reset，
    区别只是这里用 pytest fixture 实现（requests 调接口），面试讲的时候说 fixture 即可。
    注意：因为每条用例都用唯一用户名/商品名自包含（helpers.unique_username），
    不重置也能重复跑；这个 fixture 是给「每次全量回归都从干净库开始」用的，整场只跑一次。
    """
    r = requests.post(f"{BASE_URL}/api/reset")
    assert r.status_code == 200, f"/api/reset 失败: {r.text}"


@pytest.fixture
def api():
    """一个干净的、未登录的客户端（用来测未授权场景）"""
    return ApiClient()


@pytest.fixture
def admin():
    """已登录的管理员（独立客户端，需先 `python seed_admin.py` 生成 admin/admin123）"""
    c = ApiClient()
    c.login("admin", "admin123")
    return c


@pytest.fixture
def user():
    """一个已注册并登录的普通用户（独立客户端，每条用例一个，互不干扰）"""
    c = ApiClient()
    register_user(c)
    return c
