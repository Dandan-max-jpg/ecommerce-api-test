# run_all.py —— 一键运行入口：PyCharm 里右键 Run 即可，不用记任何命令
#
# 做的事和 run_tests.cmd 完全一致：
#   [1/4] 初始化管理员账号（seed_admin.py，幂等，重复跑不会出错）
#   [2/4] 确保被测服务在 5000 端口在线（已在跑就直接复用，不会重复起、也不会关它）
#   [3/4] 运行 pytest（自动读 pytest.ini 的 addopts：-v --alluredir=reports/allure）
#   [4/4] 打印退出码 + 查看 Allure 报告的命令
#
# 用法：
#   PyCharm：右键 run_all.py -> Run 'run_all'
#   终端：  python run_all.py              （跑全部用例）
#           python run_all.py -k smoke     （额外参数原样透传给 pytest）

import os
import sys
import time
import threading
import subprocess

# 不管 PyCharm 把工作目录设成哪，都先切到本文件所在目录，相对路径才不会错
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import requests

BASE_URL = "http://127.0.0.1:5000"


def app_alive():
    """5000 端口是否已有被测服务在跑"""
    try:
        return requests.get(f"{BASE_URL}/api/health", timeout=1).status_code == 200
    except Exception:
        return False


def wait_alive(timeout_s=30):
    for _ in range(timeout_s * 2):
        if app_alive():
            return True
        time.sleep(0.5)
    return False


def start_server():
    """在当前进程里用守护线程起 Flask。
    debug=True：与手工 python app.py 行为一致（D20 调试页泄露这条缺陷只在 debug 模式下复现）；
    use_reloader=False：关掉热重载，避免再造一个子进程抢 5000 端口。"""
    from app import app
    t = threading.Thread(target=lambda: app.run(debug=True, use_reloader=False), daemon=True)
    t.start()


def main():
    print("=" * 62)
    print(" 一键回归：建管理员 -> 确保服务在线 -> pytest -> 汇总")
    print("=" * 62)

    print("[1/4] 初始化管理员账号 admin/admin123 ...")
    subprocess.run([sys.executable, "seed_admin.py"], check=False)

    started_here = False
    if app_alive():
        print("[2/4] 检测到 5000 端口已有被测服务，直接复用（结束后不会关它）")
    else:
        print("[2/4] 启动被测服务（debug=True，与手工启动行为一致）...")
        start_server()
        started_here = True
        if not wait_alive(30):
            print("!! 服务 30 秒内未就绪，终止。")
            sys.exit(1)

    extra = sys.argv[1:]
    print("[3/4] 运行 pytest ..." + (f"（透传参数：{' '.join(extra)}）" if extra else ""))
    code = subprocess.run([sys.executable, "-m", "pytest"] + extra).returncode

    print("[4/4] 结束，pytest 退出码：", code)
    print("查看 Allure 报告：  allure serve reports/allure")
    if started_here:
        print("被测服务随本脚本退出自动关闭。")
    sys.exit(code)


if __name__ == "__main__":
    main()
