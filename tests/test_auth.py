# test_auth.py —— 认证模块：TC01 ~ TC07
#
# 用例编号与《测试用例设计表》一一对应（test_tcNN_xxx）。
# 标 xfail 的用例 = 已知缺陷：断言写的是"系统应该怎样"，实际没达标 → 黄色 xfail。
# strict=True：一旦开发把缺陷修好，这条会变 XPASS 并让 CI 变红，
#              提醒我们把 xfail 摘掉 —— 这是管理"已知缺陷"的专业做法。
import pytest
import allure
from helpers import unique_username


@allure.feature("认证模块")
@allure.story("注册")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc01_register_normal(api):
    """TC01 正常注册：合法用户名 + 合规密码 → 200"""
    r = api.register(unique_username(), "Test1234")
    assert r.status_code == 200


@allure.feature("认证模块")
@allure.story("注册(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D1: 注册未校验用户名非空", strict=True)
def test_tc02_D1_register_empty_username_should_400(api):
    """TC02 空用户名注册：应 400 拦截，但系统未校验 → 200"""
    assert api.register("", "test123").status_code == 400


@allure.feature("认证模块")
@allure.story("注册(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D1: 注册未校验密码长度(应>=6)", strict=True)
def test_tc03_D1_register_short_password_should_400(api):
    """TC03 密码小于 6 位：应 400 拦截，但系统未校验 → 200"""
    assert api.register(unique_username(), "12").status_code == 400


@allure.feature("认证模块")
@allure.story("注册")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.xfail(reason="已知缺陷 D15: 重复注册把 SQLite 原始异常直接透传给客户端", strict=True)
def test_tc04_D15_register_duplicate_should_not_leak_sqlite_error(api):
    """TC04 重复用户名：应 400 + 友好业务提示，实际把 UNIQUE 约束异常原文吐给客户端"""
    name = unique_username("dup_")
    assert api.register(name, "Test1234").status_code == 200
    r = api.register(name, "Test1234")
    # 状态码这一步系统是对的（400），真正的缺陷是响应体泄露了数据库原始错误
    assert r.status_code == 400, f"重复注册状态码异常: {r.status_code}"
    leaked = ("UNIQUE" in r.text) or ("sqlite" in r.text.lower())
    assert not leaked, f"响应泄露了数据库原始异常: {r.text}"


@allure.feature("认证模块")
@allure.story("登录")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc05_login_normal(api):
    """TC05 正常登录：→ 200 且返回 token"""
    name = unique_username()
    api.register(name, "Test1234")
    r = api.login(name, "Test1234")
    assert r.status_code == 200
    assert api.token is not None


@allure.feature("认证模块")
@allure.story("登录")
@allure.severity(allure.severity_level.NORMAL)
def test_tc06_login_wrong_password_401(api):
    """TC06 错误密码：→ 401"""
    name = unique_username()
    api.register(name, "Test1234")
    assert api.login(name, "wrongpwd").status_code == 401


@allure.feature("认证模块")
@allure.story("登录")
@allure.severity(allure.severity_level.NORMAL)
def test_tc07_login_unknown_user_401(api):
    """TC07 用户不存在：→ 401"""
    assert api.login(unique_username("ghost_"), "Test1234").status_code == 401
