# test_ddt.py —— 数据驱动（YAML）示例
# 演示"用例数据与代码分离"：加等价类用例只改 data/register_cases.yaml。
# 注意：defect 非空的用例用 pytest.param(... marks=xfail) 登记为"已知缺陷"，
#       跑出来是黄色 xfail，而不是红色失败——这正是专业测试管理缺陷的方式。
import os
import pytest
import yaml
import allure
from api_client import ApiClient
from helpers import unique_username

_DATA = os.path.join(os.path.dirname(__file__), "data")
_with_params = []
for _c in yaml.safe_load(open(os.path.join(_DATA, "register_cases.yaml"), encoding="utf-8")):
    _marks = [pytest.mark.xfail(reason=f"已知缺陷 {_c['defect']}", strict=False)] if _c.get("defect") else []
    _with_params.append(pytest.param(_c, id=_c["case"], marks=_marks))


@allure.feature("认证模块")
@allure.story("注册(数据驱动)")
@pytest.mark.parametrize("c", _with_params)
def test_register_ddt(c, api):
    # 缺失用户名的用例才真正传 null（测"未传"）；其余一律用唯一用户名，
    # 避免持久化数据库里固定用户名被重复注册导致偶发碰撞。
    name = None if c["username"] is None else unique_username()
    r = api.register(name, c["password"])
    assert r.status_code == c["expect_status"]
