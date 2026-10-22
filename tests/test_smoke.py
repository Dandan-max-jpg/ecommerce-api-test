# test_smoke.py —— 起步冒烟（2 条）：服务存活 + 注册正常
# 说明：D1(空用户名未校验) 这类缺陷用例已迁移到 test_ddt.py，并以 xfail 登记，
#       这里只保留永远能通过的基础冒烟，保证 `pytest` 默认就是绿 + 黄(xfail)。
import time


def test_health(api):
    """冒烟：服务活着"""
    r = api.request("GET", "/api/health")
    assert r.status_code == 200


def test_register_normal(api):
    """正常等价类：合法用户名 + 合规密码 → 200"""
    uname = "u" + str(int(time.time()))
    r = api.register(uname, "test123")
    assert r.status_code == 200
