# test_smoke.py —— 冒烟：只留"服务存活"这一条永远该绿的基线
# 说明：注册/登录等正常流程用例已归入 test_auth.py 的 TC01~TC07，
#       这里不再重复，避免同一条用例在报告里出现两次。
import allure


@allure.feature("冒烟")
@allure.story("健康检查")
@allure.severity(allure.severity_level.BLOCKER)
def test_smoke_health(api):
    """冒烟：服务活着就返回 200 且 status=ok（跑用例前确认环境没挂）"""
    r = api.health()
    assert r.status_code == 200
    assert api.ok_data(r)["status"] == "ok"
