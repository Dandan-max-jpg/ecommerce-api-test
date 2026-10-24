# test_orders.py —— 订单模块：TC32 ~ TC37、TC50
#
# 覆盖缺陷：D9(未校验库存→超卖) D10(round 假四舍五入，1.005 入库变 1.0，丢 1 分)
# 方法：等价类 + 边界值 + 金额精度专项。
import pytest
import allure
from helpers import create_product


@allure.feature("订单模块")
@allure.story("创建订单")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc32_create_order_normal(user, admin):
    """TC32 库存充足下单 → 200，状态 pending，金额正确"""
    pid = create_product(admin, price=10.0, stock=100)
    user.add_cart(pid, 3)
    r = user.create_order()
    assert r.status_code == 200
    d = user.ok_data(r)
    assert d["status"] == "pending"
    assert d["total"] == 30.0


@allure.feature("订单模块")
@allure.story("创建订单(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc33_create_order_empty_cart_400(user):
    """TC33 空购物车下单 → 400（系统正确拦截，基线用例）"""
    assert user.create_order().status_code == 400


@allure.feature("订单模块")
@allure.story("创建订单(业务规则)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D9: 下单未校验库存，可超卖", strict=True)
def test_tc34_D9_create_order_oversell_should_400(user, admin):
    """TC34 库存只有 1 却买 100 件，应 400 库存不足，但系统照常创建 → 200"""
    pid = create_product(admin, price=10.0, stock=1)
    user.add_cart(pid, 100)
    assert user.create_order().status_code == 400


@allure.feature("订单模块")
@allure.story("创建订单(认证)")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc35_create_order_without_token_401(api):
    """TC35 未登录下单 → 401"""
    assert api.create_order().status_code == 401


@allure.feature("订单模块")
@allure.story("查询订单")
@allure.severity(allure.severity_level.NORMAL)
def test_tc36_list_orders_normal(user, admin):
    """TC36 我的订单 → 200 且列表非空"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    user.create_order()
    r = user.list_orders()
    assert r.status_code == 200
    assert len(user.ok_data(r)) >= 1


@allure.feature("订单模块")
@allure.story("订单详情")
@allure.severity(allure.severity_level.NORMAL)
def test_tc37_order_detail_normal(user, admin):
    """TC37 订单详情 → 200 且含 order 明细"""
    pid = create_product(admin)
    user.add_cart(pid, 1)
    oid = user.ok_data(user.create_order())["order_id"]
    r = user.order_detail(oid)
    assert r.status_code == 200
    assert "order" in user.ok_data(r)


@allure.feature("订单模块")
@allure.story("金额精度")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.xfail(reason="已知缺陷 D10: round 假四舍五入，1.005 入库变 1.0，凭空少 1 分", strict=True)
def test_tc50_D10_order_total_float_precision(user, admin):
    """TC50 单价 1.005 买 1 件：应付 1.01，系统 round(1.005,2) 得 1.0

    排查过程：一开始想复现 0.1+0.2 那种累加误差，但服务端在落库前做了 round(total,2)
    把误差盖住了；再往下看才发现真正的坑是 Python 的 round 是"假四舍五入"——
    1.005 在二进制里其实是 1.004999…，round 之后是 1.0 而不是 1.01。
    """
    pid = create_product(admin, price=1.005, stock=100)
    user.add_cart(pid, 1)
    d = user.ok_data(user.create_order())
    assert d["total"] == 1.01, f"金额精度错误：应 1.01，实际 {d['total']}"
