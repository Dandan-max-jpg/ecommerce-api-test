# run_all.py —— 一键运行入口
#
# 做的事和 run_tests.cmd 完全一致：
#   [1/4] 初始化管理员账号（seed_admin.py，幂等，重复跑不会出错）
#   [2/4] 确保被测服务在 5000 端口在线（已在跑就直接复用，不会重复起、也不会关它）
#   [3/4] 运行 pytest（自动读 pytest.ini 的 addopts：-v --alluredir=reports/allure）
#   [4/4] 生成 Allure 报告并在浏览器自动打开（检测不到 allure 时退回为打印手动命令）
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
import functools
import glob
import http.server
import shutil
import socket
import webbrowser

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


def find_allure():
    """找 allure 命令行工具：先看 PATH，再按常见安装位置兜底。
    （刚装好/刚改 PATH 后，已开着的 PyCharm 是旧环境快照，PATH 里可能还没有它，
      所以多兜一层 D:\\allure\\allure-*\\bin\\allure.bat 这种常见安装布局）"""
    exe = shutil.which("allure") or shutil.which("allure.bat")
    if exe:
        return exe
    hits = glob.glob(r"D:\allure\allure-*\bin\allure.bat")
    return sorted(hits)[-1] if hits else None


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """报告页的每次静态资源请求都不往控制台刷日志"""

    def log_message(self, *args):
        pass


def open_report():
    """把 pytest 产出的原始结果渲染成 HTML 报告，起本地服务并自动打开浏览器。
    返回 True 表示报告服务已启动（调用方需等用户回车再退出，否则服务随进程消失）。"""
    allure = find_allure()
    if not allure:
        print("未检测到 allure 命令行工具，本次不自动打开报告。")
        print("安装 allure-commandline 后可用：  allure serve reports/allure")
        return False

    print("正在生成 Allure 报告（reports/allure -> reports/allure-html）...")
    # allure.bat 需要 java：系统没配 JAVA_HOME 且 PATH 也找不到 java 时，按常见位置兜底找一次
    env = os.environ.copy()
    if not env.get("JAVA_HOME") and not shutil.which("java"):
        jdk_hits = glob.glob(r"D:\Dev\Java\jdk-*\bin\java.exe")
        if jdk_hits:
            env["JAVA_HOME"] = os.path.dirname(os.path.dirname(sorted(jdk_hits)[-1]))
    # allure.bat 在中文 Windows 上输出是 GBK：必须指定解码，否则 Python 按 UTF-8 解会直接崩
    r = subprocess.run(
        [allure, "generate", "reports/allure", "-o", "reports/allure-html", "--clean"],
        capture_output=True, text=True, encoding="gbk", errors="replace", env=env,
    )
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip()[-500:]
        print("Allure 报告生成失败：", tail)
        print("可手动执行：  allure serve reports/allure")
        return False

    # 找一个空闲端口，把 reports/allure-html 当静态站点起在本机（127.0.0.1）
    try:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        handler = functools.partial(_QuietHandler, directory=os.path.join(ROOT, "reports", "allure-html"))
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{port}"
        webbrowser.open(url)
        print(f"Allure 报告已生成并在浏览器打开：{url}")
        print("（报告同时保存在 reports\\allure-html，以后可双击 index.html 或用 allure open 查看）")
        return True
    except Exception as e:
        # 报告只是"锦上添花"，任何一步失败都不能影响主流程和退出码
        print(f"自动打开报告失败（{e}），可手动执行：  allure serve reports/allure")
        return False


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
    report_ready = open_report()
    if report_ready:
        input("\n报告服务运行中，浏览器没自动弹出就手动打开上面的地址。按回车键退出...")
    if started_here:
        print("被测服务随本脚本退出自动关闭。")
    sys.exit(code)


if __name__ == "__main__":
    main()
