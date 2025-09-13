@echo off
cd /d "D:\SeedAI\open-webui-main2\open-webui\backend"
python -c "import uvicorn; uvicorn.run('open_webui.main:app', host='0.0.0.0', port=8080, forwarded_allow_ips='*', log_level='info')"
pause