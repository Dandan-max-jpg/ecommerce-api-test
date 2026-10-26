# 电商交易系统 · 接口自动化测试

![CI](https://github.com/Dandan-max-jpg/ecommerce-api-test/actions/workflows/test.yml/badge.svg)

> 用 pytest 给一个 Flask 电商后端写的接口自动化测试框架：**55 条用例，一跑就是
> `27 passed, 28 xfailed`** —— 绿的是"系统做对了"，黄的是"已知缺陷，证据已固化"。

## 一、用例与缺陷覆盖

用例编号覆盖 **TC01 ~ TC51**，缺陷覆盖 **D1 ~ D20** 全部 20 条：

| 项 | 数量 | 说明 |
|---|---|---|
| 用例总数 | 55 | TC01~TC51 各 1 条 + 冒烟 1 条 + 数据驱动 3 条 |
| 通过（绿） | 27 | 正常流程与"系统正确拒绝"的基线用例 |
| 已知缺陷（黄 xfail） | 28 | 覆盖 D1~D20，断言写的是"应该怎样"，实际没达标 |

**为什么把缺陷跑成"黄色"而不是"红色"**：缺陷是已知且未修的，用
`@pytest.mark.xfail(reason="已知缺陷 Dxx: ...", strict=True)` 登记。
`strict=True` 是关键——哪天开发把缺陷修好了，这条会变 **XPASS 并让 CI 变红**，
逼我们回来把 xfail 摘掉。这是管理已知缺陷的专业做法，不是"把红灯藏起来"。

## 二、缺陷 → 用例对照（20 个全覆盖）

| 缺陷 | 一句话 | 对应用例 |
|---|---|---|
| D1 | 注册未校验用户名非空 / 密码长度 | `test_tc02_D1` `test_tc03_D1` + DDT×2 |
| D2 | 商品列表未校验 page/size 负数 | `test_tc09_D2` `test_tc10_D2` |
| D3 | 非管理员也能建商品（越权） | `test_tc12_D3` |
| D4 | 建商品 price/stock 传字符串 → 500 | `test_tc15_D4` `test_tc16_D4` |
| D5 | 建商品负数价格/库存被接受 | `test_tc13_D5` `test_tc14_D5` |
| D6 | 加购 product_id 传字符串 → 500 | `test_tc25_D6` |
| D7 | 加购数量 ≤0 未校验 | `test_tc23_D7` `test_tc24_D7` |
| D8 | 删不存在的购物车项仍 200 | `test_tc30_D8` |
| D9 | 下单未校验库存（超卖） | `test_tc34_D9` |
| D10 | `round` 假四舍五入，1.005 变 1.0 丢 1 分 | `test_tc50_D10` |
| D11 | 支付未校验负数金额 | `test_tc38_D11` |
| D12 | 已支付订单可重复支付 | `test_tc39_D12` |
| D13 | 已支付订单仍可取消 | `test_tc41_D13` |
| D14 | 未发货即可确认收货（状态机缺失） | `test_tc43_D14` |
| D15 | 重复注册把 SQLite 原始异常透传给客户端 | `test_tc04_D15` |
| D16 | 幽灵商品可加购，下单级联 500 | `test_tc49_D16` |
| D17 | 改商品 price 传字符串 → 500 | `test_tc21_D17` |
| D18 | 改商品负数价格/库存被接受 | `test_tc46_D18` `test_tc47_D18` |
| D19 | 改不存在的商品仍返回 200 | `test_tc48_D19` |
| D20 | 500 调试页泄露 SECRET 与堆栈 | `test_tc51_D20` |

> 缺陷号已写进用例函数名，所以**命令行任何宽度下都能一眼看到是哪条缺陷**
> （终端太窄时 pytest 会省略行尾的 xfail 原因，但函数名不会被截断）。

## 三、项目简介

被测系统是用 Flask 写的电商后端（注册 / 登录 / 商品 / 购物车 / 订单 / 支付），
围绕它共设计 **51 条手工用例**（等价类 / 边界值 / 异常 / 状态机 / 安全性），
并搭建这套 pytest 框架让用例可以一键回归，由 GitHub Actions 每次提交自动跑。

## 四、测试流程

1. **用例设计**：围绕 16 个业务接口，按等价类 / 边界值 / 异常 / 状态机 / 安全性设计 51 条手工用例（TC01~TC51）。
2. **手工执行**：在 Apifox 中逐条执行全部接口，定位并记录 20 个缺陷（D1~D20），包括越权、订单状态机缺失、金额校验缺失、浮点精度丢分、密钥泄露等。
3. **自动化回归**：按手工用例逐条落地为 pytest 用例，命中缺陷的用例以 `xfail(strict=True)` 登记，形成可一键回归的自动化套件（共 55 条）。
4. **持续集成**：GitHub Actions 在每次提交时自动启动被测服务、跑全量用例、输出报告。

## 五、技术栈

`pytest` · `requests` · `PyYAML`（数据驱动）· `Allure`（报告） · `GitHub Actions`（CI） · `Flask`（被测系统）

## 六、目录结构

```
.
├── app.py / seed_admin.py        # 被测系统（故意保留 20 个已知缺陷，供接口测试练习）
├── tests/
│   ├── api_client.py             # 第1层：接口封装（自动带 Bearer token）
│   ├── helpers.py                # 第2层：造数工具（随机用户名 / 注册 / 建商品）
│   ├── conftest.py               # 第3层：夹具（清库 + admin/user/api 三种客户端）
│   ├── test_auth.py              # 第4层：TC01~TC07   认证模块
│   ├── test_products.py          #           TC08~TC21 / TC46~TC48 / TC51  商品模块
│   ├── test_cart.py              #           TC22~TC31 / TC49            购物车模块
│   ├── test_orders.py            #           TC32~TC37 / TC50            订单模块
│   ├── test_order_state.py       #           TC38~TC45  支付/发货/取消/确认（状态机）
│   ├── test_ddt.py               # 第5层：数据驱动（YAML 驱动注册等价类）
│   └── data/register_cases.yaml
├── .github/workflows/test.yml    # CI：提交即起服务 + 跑测试 + 出报告
└── requirements.txt / pytest.ini / run_tests.cmd / run_all.py
```

## 七、怎么跑（本地）

**推荐（一键，零记命令）**：在 PyCharm 里右键 `run_all.py` → Run，或在终端执行：

```bash
python run_all.py
```

脚本会自动：建管理员 → 按需起被测服务（已在跑则复用，不会误杀） → 跑全套 pytest → 提示看报告。
跟在后面的参数会原样透传给 pytest，例如只跑冒烟：

```bash
python run_all.py -k smoke
```

**手动分步（等价于上面的脚本）**：

```bash
pip install -r requirements.txt
python seed_admin.py      # 初始化 admin/admin123
python app.py             # 启动被测服务（5000 端口，开一个新终端）
pytest                    # 另开终端跑测试
```

**Windows 一键批处理**：直接双击 `run_tests.cmd`（建账号 → 起服务 → 等健康检查 → 跑测试 → 关闭）。
脚本里加了 `mode con: cols=170`：**终端宽度不够时，pytest 会把行尾的 xfail 原因省略掉**，调宽列数能看全。

## 八、怎么读结果

```
tests/test_products.py::test_tc15_D4_create_product_string_price_should_400 XFAIL [ 80%]
                                        ↑ 用例编号      ↑ 缺陷号
```

- `PASSED` = 系统行为符合预期（正常流程 + 正确拒绝的边界都该绿）
- `XFAIL` = 已知缺陷，断言写的是"应该怎样"，实际没达标，证据固化在这里
- `FAILED` = 真出问题了（要么被测系统改坏了，要么有新缺陷）—— CI 会拦住

## 九、典型缺陷（节选）

- **D3 越权**：普通用户也能建商品（应 403，实 200）
- **D14 状态机缺失**：未发货的订单可直接确认收货（应 400，实 200）
- **D10 浮点精度**：单价 `1.005` 经 `round` 后变 `1.0`，账上少 1 分
- **D20 信息泄露**：500 调试页把 SECRET 密钥和堆栈返回给客户端

以上 4 条为典型代表，全部 20 条缺陷与用例的完整对照见第二节表格。

---

**作者**：吴嘉乐
