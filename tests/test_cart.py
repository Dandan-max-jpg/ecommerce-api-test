# test_cart.py —— 购物车模块用例
# 设计方法：等价类 + 边界值。D6(类型)、D7(数量边界)、D8(越权/不存在) 标 xfail。
import pytest
import allure
from helpers import create_product


@allure.feature("购物车模块")
@allure.story("加入购物车")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_cart_normal(user, admin):
    """合法加购 → 200"""
    pid = create_product(admin)
    assert user.add_cart(pid, 2).status_code == 200


@allure.feature("购物车模块")
@allure.story("加入购物车(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D6: product_id 传字符串 -> 500", strict=False)
def test_add_cart_string_product_id_should_400(user, admin):
    """product_id="abc" 应 400，但系统 int() 抛异常 → 500"""
    assert user.add_cart("abc", 1).status_code == 400


@allure.feature("购物车模块")
@allure.story("加入购物车(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D7: 未校验数量<=0", strict=False)
def test_add_cart_quantity_zero_should_400(user, admin):
    """quantity=0 应 400，但系统接受 → 200"""
    pid = create_product(admin)
    assert user.add_cart(pid, 0).status_code == 400


@allure.feature("购物车模块")
@allure.story("加入购物车(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D7: 未校验数量<=0", strict=False)
def test_add_cart_quantity_negative_should_400(user, admin):
    """quantity=-3 应 400，但系统接受 → 200（会导致库存被加负）"""
    pid = create_product(admin)
    assert user.add_cart(pid, -3).status_code == 400


@allure.feature("购物车模块")
@allure.story("查看购物车")
@allure.severity(allure.severity_level.NORMAL)
def test_view_cart(user, admin):
    """加购后能查到 → 200 且列表非空"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    r = user.view_cart()
    assert r.status_code == 200
    assert len(user.ok_data(r)) >= 1


@allure.feature("购物车模块")
@allure.story("删除购物车项")
@allure.severity(allure.severity_level.NORMAL)
def test_delete_cart_existing(user, admin):
    """删除自己存在的购物车项 → 200"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    item_id = user.ok_data(user.view_cart())[0]["id"]
    assert user.del_cart(item_id).status_code == 200


@allure.feature("购物车模块")
@allure.story("删除购物车项(边界值)")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.xfail(reason="已知缺陷 D8: 删不存在的项未校验 -> 200", strict=False)
def test_delete_cart_nonexistent_should_404(user):
    """删除不存在的购物车项应 404，但系统直接 DELETE 返回 200"""
    assert user.del_cart(99999999).status_code == 404


@allure.feature("购物车模块")
@allure.story("删除购物车项(越权)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D8: 删别人的项未校验归属 -> 200", strict=False)
def test_delete_cart_other_user_should_404(user, admin):
    """A 加购、B 来删 A 的项应 404，但系统不校验归属 → 200（越权）"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    item_id = user.ok_data(user.view_cart())[0]["id"]
    # 用另一个普通用户去删
    from helpers import register_user
    other = admin.__class__()  # 新的干净客户端
    register_user(other)
    assert other.del_cart(item_id).status_code == 404
