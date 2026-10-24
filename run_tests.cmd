@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 把控制台加宽到 170 列：终端太窄时 pytest 会把 xfail 后面的「已知缺陷 Dxx」原因省略掉
mode con: cols=170 lines=60

REM 优先用本机 python（若 D:\Dev\Python313 在 PATH 则直接用 python）
set PY=python
where python >nul 2>nul || set PY=py

echo [1/4] 初始化管理员账号...
%PY% seed_admin.py

echo [2/4] 后台启动被测服务...
start "" %PY% app.py

echo [3/4] 等待服务健康检查...
set /a n=0
:wait
curl -s http://127.0.0.1:5000/api/health | findstr ok >nul && goto run
timeout /t 1 >nul
set /a n+=1
if %n% lss 30 goto wait

:run
echo [4/4] 运行 pytest 并生成 Allure 结果...
%PY% -m pytest -v --alluredir=reports/allure

echo 测试结束。查看报告：allure serve reports/allure
echo 关闭后台被测服务...
taskkill /f /im python.exe >nul 2>nul
pause
