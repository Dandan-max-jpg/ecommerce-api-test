# test_products.py —— 商品模块：TC08 ~ TC21、TC46 ~ TC48，另加 D20 安全缺陷
#
# 覆盖缺陷：D2(分页越界) D3(越权建商品) D4(类型未校验→500) D5(负数被接受)
#           D17(改商品类型→500) D18(改商品负数被接受) D19(改不存在的商品仍 200)
#           D20(500 调试页泄露 SECRET 密钥)
# 方法：等价类 + 边界值 + 权限校验 + 安全性。
import pytest
import allure
from helpers import create_product


@allure.feature("商品模块")
@allure.story("列表")
@allure.severity(allure.severity_level.NORMAL)
def test_tc08_product_list_default(admin):
    """TC08 商品列表正常分页 → 200 且返回数组"""
    r = admin.list_products(page=1, size=10)
    assert r.status_code == 200
    assert isinstance(admin.ok_data(r), list)


@allure.feature("商品模块")
@allure.story("列表(边界值)")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.xfail(reason="已知缺陷 D2: 未校验 page 为负数(静默当 0)", strict=True)
def test_tc09_D2_product_list_negative_page_should_400(admin):
    """TC09 page=-1 应 400，但系统未校验 → 200"""
    assert admin.list_products(page=-1, size=10).status_code == 400


@allure.feature("商品模块")
@allure.story("列表(边界值)")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.xfail(reason="已知缺陷 D2: 未校验 size 为负数(LIMIT 变负→返回全部)", strict=True)
def test_tc10_D2_product_list_negative_size_should_400(admin):
    """TC10 size=-5 应 400，但系统未校验 → 200"""
    assert admin.list_products(page=1, size=-5).status_code == 400


@allure.feature("商品模块")
@allure.story("创建")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc11_create_product_admin_normal(admin):
    """TC11 管理员建合法商品 → 200 且返回 id"""
    r = admin.create_product("键盘", 199.9, 10, "3C")
    assert r.status_code == 200
    assert admin.ok_data(r)["id"] > 0


@allure.feature("商品模块")
@allure.story("创建(权限)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D3: 非管理员也能建商品(越权)", strict=True)
def test_tc12_D3_create_product_non_admin_should_403(user):
    """TC12 普通用户建商品应 403，但系统未校验角色 → 200"""
    assert user.create_product("越权商品", 1.0, 1).status_code == 403


@allure.feature("商品模块")
@allure.story("创建(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D5: 未校验负价格", strict=True)
def test_tc13_D5_create_product_negative_price_should_400(admin):
    """TC13 price=-9.9 应 400，但系统接受 → 200"""
    assert admin.create_product("负价商品", -9.9, 5).status_code == 400


@allure.feature("商品模块")
@allure.story("创建(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D5: 未校验负库存", strict=True)
def test_tc14_D5_create_product_negative_stock_should_400(admin):
    """TC14 stock=-3 应 400，但系统接受 → 200"""
    assert admin.create_product("负库存商品", 10.0, -3).status_code == 400


@allure.feature("商品模块")
@allure.story("创建(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D4: price 传字符串直接 float() 抛异常 → 500", strict=True)
def test_tc15_D4_create_product_string_price_should_400(admin):
    """TC15 price="abc" 应 400 友好拒绝，但系统未做类型校验 → 500"""
    assert admin.create_product("类型异常", "abc", 3).status_code == 400


@allure.feature("商品模块")
@allure.story("创建(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D4: stock 传字符串直接 int() 抛异常 → 500", strict=True)
def test_tc16_D4_create_product_string_stock_should_400(admin):
    """TC16 stock="abc" 应 400 友好拒绝，但系统未做类型校验 → 500"""
    assert admin.create_product("类型异常", 10.0, "abc").status_code == 400


@allure.feature("商品模块")
@allure.story("查询")
@allure.severity(allure.severity_level.NORMAL)
def test_tc17_get_product_existing(admin):
    """TC17 存在的商品详情 → 200"""
    pid = create_product(admin)
    assert admin.get_product(pid).status_code == 200


@allure.feature("商品模块")
@allure.story("查询")
@allure.severity(allure.severity_level.NORMAL)
def test_tc18_get_product_nonexistent_404(admin):
    """TC18 不存在的商品 → 404"""
    assert admin.get_product(99999999).status_code == 404


@allure.feature("商品模块")
@allure.story("修改")
@allure.severity(allure.severity_level.NORMAL)
def test_tc19_update_product_admin_normal(admin):
    """TC19 管理员改价 → 200"""
    pid = create_product(admin)
    assert admin.update_product(pid, price=179.9).status_code == 200


@allure.feature("商品模块")
@allure.story("修改(权限)")
@allure.severity(allure.severity_level.CRITICAL)
def test_tc20_update_product_non_admin_403(user, admin):
    """TC20 非管理员改商品 → 403（系统正确拦截，基线用例）"""
    pid = create_product(admin)
    assert user.update_product(pid, price=179.9).status_code == 403


@allure.feature("商品模块")
@allure.story("修改(参数校验)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D17: 修改商品 price 传字符串 → 500", strict=True)
def test_tc21_D17_update_product_string_price_should_400(admin):
    """TC21 改价传 "abc" 应 400，但系统 float() 抛异常 → 500"""
    pid = create_product(admin)
    assert admin.update_product(pid, price="abc").status_code == 400


@allure.feature("商品模块")
@allure.story("修改(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D18: 修改商品未校验负价格", strict=True)
def test_tc46_D18_update_product_negative_price_should_400(admin):
    """TC46 改价为 -9.9 应 400，但系统接受 → 200"""
    pid = create_product(admin)
    assert admin.update_product(pid, price=-9.9).status_code == 400


@allure.feature("商品模块")
@allure.story("修改(边界值)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D18: 修改商品未校验负库存", strict=True)
def test_tc47_D18_update_product_negative_stock_should_400(admin):
    """TC47 改库存为 -3 应 400，但系统接受 → 200"""
    pid = create_product(admin)
    assert admin.update_product(pid, stock=-3).status_code == 400


@allure.feature("商品模块")
@allure.story("修改(异常处理)")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.xfail(reason="已知缺陷 D19: 修改不存在的商品仍返回 200(未查 rowcount)", strict=True)
def test_tc48_D19_update_nonexistent_product_should_404(admin):
    """TC48 改不存在的商品应 404，但系统无差别返回 200 updated:true"""
    assert admin.update_product(99999999, price=179.9).status_code == 404


@allure.feature("安全")
@allure.story("错误信息泄露")
@allure.severity(allure.severity_level.BLOCKER)
@pytest.mark.xfail(reason="已知缺陷 D20: 500 调试页把 SECRET 密钥和堆栈返回给客户端", strict=True)
def test_tc51_D20_error_page_should_not_leak_secret(admin):
    """TC51：触发一次 500 后，响应不该出现密钥 / 堆栈，实际全泄露（手工侧为安全检查用例）"""
    r = admin.create_product("泄露探针", "abc", 1)
    secret = "ecommerce-demo-secret-key-change-me"
    assert secret not in r.text and "Traceback" not in r.text, "500 页面泄露了密钥/堆栈"
