# test_cart.py —— 购物车模块：TC22 ~ TC31、TC49
#
# 覆盖缺陷：D6(product_id 类型→500) D7(数量 ≤0 被接受) D8(删不存在/他人项仍 200)
#           D16(幽灵商品加购未校验存在性 → 下单级联 500)
# 方法：等价类 + 边界值 + 认证校验。
import pytest
import allure
from helpers import create_product


@allure.feature("购物车模块")
@allure.story("加入购物车")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc22_add_cart_normal(user, admin):
    """TC22 合法加购 → 200"""
    pid = create_product(admin)
    assert user.add_cart(pid, 2).status_code == 200


@allure.feature("购物车模块")
@allure.story("加入购物车(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D7: 未校验数量为 0", strict=True)
def test_tc23_D7_add_cart_quantity_zero_should_400(user, admin):
    """TC23 quantity=0 应 400，但系统接受 → 200"""
    pid = create_product(admin)
    assert user.add_cart(pid, 0).status_code == 400


@allure.feature("购物车模块")
@allure.story("加入购物车(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D7: 未校验数量为负数", strict=True)
def test_tc24_D7_add_cart_quantity_negative_should_400(user, admin):
    """TC24 quantity=-1 应 400，但系统接受 → 200"""
    pid = create_product(admin)
    assert user.add_cart(pid, -1).status_code == 400


@allure.feature("购物车模块")
@allure.story("加入购物车(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D6: product_id 传字符串直接 int() 抛异常 → 500", strict=True)
def test_tc25_D6_add_cart_string_product_id_should_400(user):
    """TC25 product_id="x" 应 400，但系统未做类型校验 → 500"""
    assert user.add_cart("x", 1).status_code == 400


@allure.feature("购物车模块")
@allure.story("加入购物车(认证)")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc26_add_cart_without_token_401(api):
    """TC26 未登录加购 → 401"""
    assert api.add_cart(1, 1).status_code == 401


@allure.feature("购物车模块")
@allure.story("查看购物车")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc27_view_cart_normal(user, admin):
    """TC27 加购后能查到 → 200 且列表非空"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    r = user.view_cart()
    assert r.status_code == 200
    assert len(user.ok_data(r)) >= 1


@allure.feature("购物车模块")
@allure.story("查看购物车(认证)")
@allure.severity(allure.severity_level.NORMAL)
def test_tc28_view_cart_without_token_401(api):
    """TC28 未登录查看购物车 → 401"""
    assert api.view_cart().status_code == 401


@allure.feature("购物车模块")
@allure.story("删除购物车项")
@allure.severity(allure.severity_level.NORMAL)
def test_tc29_delete_cart_item_normal(user, admin):
    """TC29 删除自己存在的购物车项 → 200"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    item_id = user.ok_data(user.view_cart())[0]["id"]
    assert user.del_cart(item_id).status_code == 200


@allure.feature("购物车模块")
@allure.story("删除购物车项(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D8: 删不存在的购物车项未校验 → 仍返回 200", strict=True)
def test_tc30_D8_delete_cart_nonexistent_should_404(user):
    """TC30 删不存在的项应 404，但系统无差别 DELETE → 200"""
    assert user.del_cart(99999999).status_code == 404


@allure.feature("购物车模块")
@allure.story("删除购物车项(认证)")
@allure.severity(allure.severity_level.NORMAL)
def test_tc31_delete_cart_without_token_401(api):
    """TC31 未登录删除购物车项 → 401"""
    assert api.del_cart(1).status_code == 401


@allure.feature("购物车模块")
@allure.story("加入购物车(业务规则)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D16: 幽灵商品也能加购(未校验商品存在)，下单时级联 500", strict=True)
def test_tc49_D16_add_cart_ghost_product_should_400(user):
    """TC49 加购不存在的商品应 400，但系统接受 → 200，且随后下单因查不到商品直接 500"""
    r_add = user.add_cart(99999999, 1)
    r_order = user.create_order()
    # 缺陷两处：加购没拦住；更严重的是它把脏数据带到了下单，导致 500 级联
    assert r_add.status_code == 400 and r_order.status_code == 400, \
        f"加购={r_add.status_code} 下单={r_order.status_code}"
