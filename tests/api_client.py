# api_client.py —— 接口封装层（分层架构第一层）
# 作用：把"怎么发请求、怎么带 token、每个接口的路径和参数"藏起来，
#       测试用例里只写业务意图，不写 URL 细节。这是自动化框架复用性高的关键。
import requests
import allure

BASE_URL = "http://127.0.0.1:5000"


class ApiClient:
    def __init__(self):
        self.base = BASE_URL
        self.token = None  # 登录成功后自动存下 JWT

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    @allure.step("请求 {method} {path}")
    def request(self, method, path, json=None):
        resp = requests.request(method, self.base + path, json=json, headers=self._headers())
        # 把请求体 / 响应体挂到 Allure，用例失败时一眼能看现场
        allure.attach(str(json), name="request_body", attachment_type=allure.attachment_type.TEXT)
        allure.attach(resp.text, name="response_body", attachment_type=allure.attachment_type.TEXT)
        return resp

    # ---------------- 用户 / 认证 ----------------
    @allure.step("注册 username={username}")
    def register(self, username, password):
        return self.request("POST", "/api/register", json={"username": username, "password": password})

    @allure.step("登录 username={username}")
    def login(self, username, password):
        r = self.request("POST", "/api/login", json={"username": username, "password": password})
        if r.status_code == 200:
            try:
                self.token = r.json().get("data", {}).get("token")
            except Exception:
                pass
        return r

    @allure.step("健康检查")
    def health(self):
        return self.request("GET", "/api/health")

    # ---------------- 商品 ----------------
    @allure.step("列出商品 page={page} size={size}")
    def list_products(self, page=1, size=10):
        return self.request("GET", f"/api/products?page={page}&size={size}")

    @allure.step("创建商品 name={name}")
    def create_product(self, name, price, stock, category=""):
        return self.request("POST", "/api/products",
                            json={"name": name, "price": price, "stock": stock, "category": category})

    @allure.step("获取商品 id={pid}")
    def get_product(self, pid):
        return self.request("GET", f"/api/products/{pid}")

    @allure.step("更新商品 id={pid}")
    def update_product(self, pid, price=None, stock=None, name=None):
        body = {}
        if price is not None:
            body["price"] = price
        if stock is not None:
            body["stock"] = stock
        if name is not None:
            body["name"] = name
        return self.request("PUT", f"/api/products/{pid}", json=body)

    # ---------------- 购物车 ----------------
    @allure.step("加入购物车 product_id={product_id} qty={quantity}")
    def add_cart(self, product_id, quantity=1):
        return self.request("POST", "/api/cart/items", json={"product_id": product_id, "quantity": quantity})

    @allure.step("查看购物车")
    def view_cart(self):
        return self.request("GET", "/api/cart")

    @allure.step("删除购物车项 id={item_id}")
    def del_cart(self, item_id):
        return self.request("DELETE", f"/api/cart/items/{item_id}")

    # ---------------- 订单 ----------------
    @allure.step("创建订单")
    def create_order(self):
        return self.request("POST", "/api/orders")

    @allure.step("列出订单")
    def list_orders(self):
        return self.request("GET", "/api/orders")

    @allure.step("订单详情 id={oid}")
    def order_detail(self, oid):
        return self.request("GET", f"/api/orders/{oid}")

    @allure.step("支付订单 id={oid}")
    def pay_order(self, oid, amount=None):
        body = {}
        if amount is not None:
            body["amount"] = amount
        return self.request("POST", f"/api/orders/{oid}/pay", json=body)

    @allure.step("取消订单 id={oid}")
    def cancel_order(self, oid):
        return self.request("POST", f"/api/orders/{oid}/cancel")

    @allure.step("发货 id={oid}")
    def ship_order(self, oid):
        return self.request("POST", f"/api/orders/{oid}/ship")

    @allure.step("确认收货 id={oid}")
    def confirm_order(self, oid):
        return self.request("POST", f"/api/orders/{oid}/confirm")

    # ---------------- 工具 ----------------
    def ok_data(self, resp):
        """从统一响应里取 data 字段（响应结构：{code, data} 或 {code, msg}）"""
        try:
            return resp.json().get("data")
        except Exception:
            return None
