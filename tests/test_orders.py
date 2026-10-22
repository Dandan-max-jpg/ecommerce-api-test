# test_orders.py —— 订单模块用例（含完整状态机 + 支付/发货/确认）
# 设计方法：等价类 + 边界值 + 状态机迁移。D9~D14 为缺陷，标 xfail。
# 注意：每条用例自己建商品、自己下单，互不依赖，可单独重跑。
import pytest
import allure
from helpers import create_product, register_user


@allure.feature("订单模块")
@allure.story("创建订单")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_order_empty_cart_400(user):
    """空购物车下单应 400（系统正确拦截）"""
    assert user.create_order().status_code == 400


@allure.feature("订单模块")
@allure.story("创建订单")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_order_normal(user, admin):
    """库存充足时下单 → 200，状态 pending，金额正确"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 3)
    r = user.create_order()
    assert r.status_code == 200
    d = user.ok_data(r)
    assert d["status"] == "pending"
    assert d["total"] == 30.0


@allure.feature("订单模块")
@allure.story("创建订单(业务规则)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D9: 未校验库存，可超卖", strict=False)
def test_create_order_oversell_should_400(user, admin):
    """库存只有 1，却下单 5 件 → 应 400（库存不足），但系统照常创建 → 200"""
    pid = create_product(admin, price=10.0, stock=1)
    user.add_cart(pid, 5)
    assert user.create_order().status_code == 400


@allure.feature("订单模块")
@allure.story("创建订单(浮点精度)")
@allure.severity(allure.severity_level.MINOR)
def test_create_order_float_precision(user, admin):
    """D10 观察项：单价 0.1 * 3 的理论和为 0.30000000000000004，
    但系统在落库前 round(total,2)，故接口返回 0.3 —— 该精度风险已被兜底，非独立可复现缺陷。
    这里用断言固化"当前行为正确"，一旦有人去掉 round 这条用例会红，起到回归守护作用。"""
    pid = create_product(admin, price=0.1, stock=100)
    user.add_cart(pid, 3)
    d = user.ok_data(user.create_order())
    assert d["total"] == 0.3


@allure.feature("订单模块")
@allure.story("查询订单")
@allure.severity(allure.severity_level.NORMAL)
def test_list_orders(user, admin):
    """下单后能查到自己订单 → 200 且列表非空"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    user.create_order()
    r = user.list_orders()
    assert r.status_code == 200
    assert len(user.ok_data(r)) >= 1


@allure.feature("订单模块")
@allure.story("订单详情")
@allure.severity(allure.severity_level.NORMAL)
def test_order_detail_existing(user, admin):
    """存在的订单 → 200，且含 order 字段"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    r = user.order_detail(oid)
    assert r.status_code == 200
    assert "order" in user.ok_data(r)


@allure.feature("订单模块")
@allure.story("订单详情")
@allure.severity(allure.severity_level.NORMAL)
def test_order_detail_nonexistent_404(user):
    """不存在的订单 → 404"""
    assert user.order_detail(99999999).status_code == 404


@allure.feature("订单模块")
@allure.story("支付")
@allure.severity(allure.severity_level.CRITICAL)
def test_pay_order_normal(user, admin):
    """待支付订单正常支付 → 状态 paid"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 2)
    oid = user.ok_data(user.create_order())["order_id"]
    r = user.pay_order(oid, amount=20.0)
    assert r.status_code == 200
    assert user.ok_data(r)["status"] == "paid"


@allure.feature("订单模块")
@allure.story("支付(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D11: 未校验负数/零金额", strict=False)
def test_pay_order_negative_amount_should_400(user, admin):
    """支付金额为 -5 应 400，但系统照常标记为 paid → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.pay_order(oid, amount=-5).status_code == 400


@allure.feature("订单模块")
@allure.story("支付(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D11: 未校验零金额", strict=False)
def test_pay_order_zero_amount_should_400(user, admin):
    """支付金额为 0 应 400，但系统照常标记为 paid → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.pay_order(oid, amount=0).status_code == 400


@allure.feature("订单模块")
@allure.story("支付(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D12: 已取消订单仍可支付", strict=False)
def test_pay_order_cancelled_should_400(user, admin):
    """订单取消后再支付应 400，但系统无状态校验 → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    user.cancel_order(oid)
    assert user.pay_order(oid, amount=10.0).status_code == 400


@allure.feature("订单模块")
@allure.story("取消订单")
@allure.severity(allure.severity_level.CRITICAL)
def test_cancel_order_pending(user, admin):
    """待支付订单取消 → 状态 cancelled"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    r = user.cancel_order(oid)
    assert r.status_code == 200
    assert user.ok_data(r)["status"] == "cancelled"


@allure.feature("订单模块")
@allure.story("取消订单(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D13: 已支付订单仍可取消", strict=False)
def test_cancel_order_paid_should_400(user, admin):
    """已支付订单再取消应 400，但系统无状态校验 → 200"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    user.pay_order(oid, amount=10.0)
    assert user.cancel_order(oid).status_code == 400


@allure.feature("订单模块")
@allure.story("发货")
@allure.severity(allure.severity_level.CRITICAL)
def test_ship_order_admin(user, admin):
    """管理员发货 → 状态 shipped"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    r = admin.ship_order(oid)
    assert r.status_code == 200
    assert admin.ok_data(r)["status"] == "shipped"


@allure.feature("订单模块")
@allure.story("确认收货")
@allure.severity(allure.severity_level.CRITICAL)
def test_confirm_order_after_shipped(user, admin):
    """已发货订单确认收货 → 状态 completed"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    user.pay_order(oid, amount=10.0)
    admin.ship_order(oid)
    r = user.confirm_order(oid)
    assert r.status_code == 200
    assert user.ok_data(r)["status"] == "completed"


@allure.feature("订单模块")
@allure.story("确认收货(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D14: 未发货(pending)即可确认", strict=False)
def test_confirm_order_before_shipped_should_400(user, admin):
    """待支付订单直接确认收货应 400，但系统无状态校验 → 200"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    assert user.confirm_order(oid).status_code == 400


@allure.feature("订单模块")
@allure.story("确认收货(状态机)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D14: 已取消订单仍可确认", strict=False)
def test_confirm_order_cancelled_should_400(user, admin):
    """已取消订单确认收货应 400，但系统无状态校验 → 200"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    user.cancel_order(oid)
    assert user.confirm_order(oid).status_code == 400
