@echo off
set BASE=http://127.0.0.1:8088/v1
set KEY=%GATEWAY_API_KEY%
if "%KEY%"=="" set KEY=changeme

echo [1] health
curl -s %BASE:/v1=%healthz || echo FAIL

echo [2] models
curl -s -H "Authorization: Bearer %KEY%" %BASE%/models || echo FAIL

echo [3] chat
curl -s -H "Authorization: Bearer %KEY%" -H "Content-Type: application/json" ^
 --data "{\"model\":\"seedai\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}" ^
 %BASE%/chat/completions || echo FAIL