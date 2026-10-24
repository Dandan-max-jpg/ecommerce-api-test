# test_order_state.py —— 支付 / 发货 / 取消 / 确认收货（订单状态机）：TC38 ~ TC45
#
# 覆盖缺陷：D11(负金额支付) D12(重复支付) D13(已支付仍可取消) D14(未发货即可确认收货)
# 方法：状态机迁移 —— 下单 → 支付 → 发货 → 确认，逐个测"能否乱跳"。
import pytest
import allure
from helpers import create_product


@allure.feature("订单状态机")
@allure.story("支付(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D11: 支付未校验负数/零金额", strict=True)
def test_tc38_D11_pay_negative_amount_should_400(user, admin):
    """TC38 支付金额 -50 应 400，但系统照常标记 paid → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.pay_order(oid, amount=-50).status_code == 400


@allure.feature("订单状态机")
@allure.story("支付(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D12: 已支付订单可重复支付(未校验订单状态)", strict=True)
def test_tc39_D12_pay_twice_should_400(user, admin):
    """TC39 同一订单付两次，第二次应 400，但系统无状态校验 → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.pay_order(oid, amount=10.0).status_code == 200
    assert user.pay_order(oid, amount=10.0).status_code == 400


@allure.feature("订单状态机")
@allure.story("支付")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc40_pay_normal(user, admin):
    """TC40 正常支付 → 200 状态 paid"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 2)
    oid = user.ok_data(user.create_order())["order_id"]
    r = user.pay_order(oid, amount=20.0)
    assert r.status_code == 200
    assert user.ok_data(r)["status"] == "paid"


@allure.feature("订单状态机")
@allure.story("取消(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D13: 已支付订单仍可取消(应仅 pending 可取消)", strict=True)
def test_tc41_D13_cancel_paid_order_should_400(user, admin):
    """TC41 已支付订单再取消应 400，但系统无状态校验 → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    user.pay_order(oid, amount=10.0)
    assert user.cancel_order(oid).status_code == 400


@allure.feature("订单状态机")
@allure.story("发货(权限)")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc42_ship_order_non_admin_403(user, admin):
    """TC42 非管理员发货 → 403（系统正确拦截，基线用例）"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.ship_order(oid).status_code == 403


@allure.feature("订单状态机")
@allure.story("确认收货(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D14: 未发货(pending)即可确认收货", strict=True)
def test_tc43_D14_confirm_before_ship_should_400(user, admin):
    """TC43 未发货订单确认收货应 400，但系统无状态校验 → 200，状态直跳 completed"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.confirm_order(oid).status_code == 400


@allure.feature("订单状态机")
@allure.story("取消订单")
@allure.severity(allure.severity_level.NORMAL)
def test_tc44_cancel_pending_order_normal(user, admin):
    """TC44 pending 订单正常取消 → 200 状态 cancelled"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    r = user.cancel_order(oid)
    assert r.status_code == 200
    assert user.ok_data(r)["status"] == "cancelled"


@allure.feature("订单状态机")
@allure.story("确认收货")
@allure.severity(allure.severity_level.NORMAL)
def test_tc45_confirm_after_ship_normal(user, admin):
    """TC45 已发货订单确认收货 → 200 状态 completed（正常状态机基线）"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    user.pay_order(oid, amount=10.0)
    admin.ship_order(oid)
    r = user.confirm_order(oid)
    assert r.status_code == 200
    assert user.ok_data(r)["status"] == "completed"
