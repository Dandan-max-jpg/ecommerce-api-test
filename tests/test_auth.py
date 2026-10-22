# test_auth.py —— 认证模块用例（功能正常用例全绿，正确拒绝用例也绿）
import time
import allure
from helpers import unique_username


@allure.feature("认证模块")
@allure.story("系统健康")
@allure.severity(allure.severity_level.BLOCKER)
def test_health(api):
    """冒烟：服务活着就返回 200"""
    r = api.health()
    assert r.status_code == 200
    assert api.ok_data(r)["status"] == "ok"


@allure.feature("认证模块")
@allure.story("注册")
@allure.severity(allure.severity_level.CRITICAL)
def test_register_normal(api):
    """有效等价类：合法用户名 + 合规密码 → 200"""
    r = api.register(unique_username(), "Test1234")
    assert r.status_code == 200


@allure.feature("认证模块")
@allure.story("注册")
@allure.severity(allure.severity_level.CRITICAL)
def test_register_duplicate_should_400(api):
    """重复用户名应被拒（UNIQUE 约束），正确返回 400 —— 这是一条'正确拒绝'用例"""
    name = unique_username("dup_")
    assert api.register(name, "Test1234").status_code == 200
    r2 = api.register(name, "Test1234")
    assert r2.status_code == 400


@allure.feature("认证模块")
@allure.story("登录")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_correct(api):
    """正确账号密码登录 → 200，且能拿到 token"""
    name = unique_username()
    api.register(name, "Test1234")
    r = api.login(name, "Test1234")
    assert r.status_code == 200
    assert api.token is not None


@allure.feature("认证模块")
@allure.story("登录")
@allure.severity(allure.severity_level.NORMAL)
def test_login_wrong_password_401(api):
    """错误密码 → 401"""
    name = unique_username()
    api.register(name, "Test1234")
    r = api.login(name, "wrongpwd")
    assert r.status_code == 401


@allure.feature("认证模块")
@allure.story("登录")
@allure.severity(allure.severity_level.NORMAL)
def test_login_nonexistent_user_401(api):
    """不存在的用户 → 401"""
    r = api.login(unique_username("ghost_"), "Test1234")
    assert r.status_code == 401


@allure.feature("认证模块")
@allure.story("授权")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_product_without_token_401(api):
    """未登录就调需要授权的接口 → 401"""
    r = api.create_product("x", 1.0, 1)
    assert r.status_code == 401
