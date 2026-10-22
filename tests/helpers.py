# helpers.py —— 测试数据准备辅助
# 目标：让每条用例"自包含、互不干扰"。每个用例自己建用户、自己建商品，
#       不依赖别的用例留下的数据，这样用例顺序无关、可单独重跑。
import time
import random
import string
from api_client import ApiClient


def rand_suffix():
    """时间戳(毫秒) + 4 位随机数字，基本保证全局唯一，避免数据库 UNIQUE 冲突"""
    return str(int(time.time() * 1000)) + "".join(random.choices(string.digits, k=4))


def unique_username(prefix="u"):
    return prefix + rand_suffix()


def register_user(api: ApiClient, password="Test1234"):
    """注册并登录一个新普通用户，返回 (username, password)"""
    uname = unique_username()
    r = api.register(uname, password)
    assert r.status_code == 200, f"注册失败: {r.status_code} {r.text}"
    api.login(uname, password)
    return uname, password


def create_product(admin_api: ApiClient, name=None, price=10.0, stock=100, category="test"):
    """以管理员身份创建一个商品，返回商品 id"""
    if name is None:
        name = "p" + rand_suffix()
    r = admin_api.create_product(name, price, stock, category)
    assert r.status_code == 200, f"建商品失败: {r.status_code} {r.text}"
    return admin_api.ok_data(r)["id"]
