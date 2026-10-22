# test_products.py —— 商品模块用例
# 设计方法：等价类 + 边界值。正常用例绿；参数校验缺失类缺陷(D2~D5)标 xfail。
import pytest
import allure
from helpers import create_product


@allure.feature("商品模块")
@allure.story("列表")
@allure.severity(allure.severity_level.NORMAL)
def test_list_products_default(admin):
    """默认分页 → 200，且返回列表"""
    r = admin.list_products()
    assert r.status_code == 200
    assert isinstance(admin.ok_data(r), list)


@allure.feature("商品模块")
@allure.story("列表(边界值)")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.xfail(reason="已知缺陷 D2: 未校验 page 为负数", strict=False)
def test_list_products_negative_page_should_400(admin):
    """page=-1 应 400（负数分页越界），但系统静默当 0 → 200"""
    assert admin.list_products(page=-1).status_code == 400


@allure.feature("商品模块")
@allure.story("列表(边界值)")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.xfail(reason="已知缺陷 D2: 未校验 size 为负数", strict=False)
def test_list_products_negative_size_should_400(admin):
    """size=-1 应 400（负数 size 被当成 LIMIT 负数 → 返回全部），系统未拦截"""
    assert admin.list_products(size=-1).status_code == 400


@allure.feature("商品模块")
@allure.story("创建")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_product_admin_normal(admin):
    """管理员建合法商品 → 200，且返回 id"""
    r = admin.create_product("iPhone", 5999.0, 50, "phone")
    assert r.status_code == 200
    assert admin.ok_data(r)["id"] > 0


@allure.feature("商品模块")
@allure.story("创建(权限)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D3: 非管理员也能建商品(越权)", strict=False)
def test_create_product_non_admin_should_403(user):
    """普通用户建商品应 403，但系统未校验角色 → 200"""
    assert user.create_product("contraband", 1.0, 1).status_code == 403


@allure.feature("商品模块")
@allure.story("创建(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D4: price 传字符串 -> 500", strict=False)
def test_create_product_string_price_should_400(admin):
    """price="abc" 应 400（类型校验），但系统直接 float() 抛异常 → 500"""
    assert admin.create_product("bad", "abc", 1).status_code == 400


@allure.feature("商品模块")
@allure.story("创建(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D4: stock 传字符串 -> 500", strict=False)
def test_create_product_string_stock_should_400(admin):
    """stock="abc" 应 400，但系统 int() 抛异常 → 500"""
    assert admin.create_product("bad", 1.0, "abc").status_code == 400


@allure.feature("商品模块")
@allure.story("创建(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D5: 未校验负价格", strict=False)
def test_create_product_negative_price_should_400(admin):
    """price=-1 应 400（金额非负），但系统接受 → 200"""
    assert admin.create_product("neg", -1.0, 10).status_code == 400


@allure.feature("商品模块")
@allure.story("创建(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D5: 未校验负库存", strict=False)
def test_create_product_negative_stock_should_400(admin):
    """stock=-5 应 400，但系统接受 → 200"""
    assert admin.create_product("neg", 1.0, -5).status_code == 400


@allure.feature("商品模块")
@allure.story("查询")
@allure.severity(allure.severity_level.NORMAL)
def test_get_product_existing(admin):
    """存在的商品 → 200"""
    pid = create_product(admin)
    assert admin.get_product(pid).status_code == 200


@allure.feature("商品模块")
@allure.story("查询")
@allure.severity(allure.severity_level.NORMAL)
def test_get_product_nonexistent_404(admin):
    """不存在的商品 → 404"""
    assert admin.get_product(99999999).status_code == 404


@allure.feature("商品模块")
@allure.story("更新(权限)")
@allure.severity(allure.severity_level.CRITICAL)
def test_update_product_non_admin_403(user, admin):
    """普通用户改商品应 403（系统正确拦截）"""
    pid = create_product(admin)
    assert user.update_product(pid, price=1.0).status_code == 403
