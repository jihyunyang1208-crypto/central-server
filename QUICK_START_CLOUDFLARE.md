# Cloudflare Tunnel 빠른 시작 (Windows)

## 1. cloudflared 다운로드
https://github.com/cloudflare/cloudflared/releases/latest
→ `cloudflared-windows-amd64.exe` 다운로드
→ `cloudflared.exe`로 이름 변경

## 2. Cloudflare 로그인
```powershell
cloudflared tunnel login
```

## 3. 터널 생성
```powershell
cloudflared tunnel create aut-central-backend
```
→ `<tunnel-id>` 복사

## 4. 설정 파일 생성
**파일:** `C:\Users\yangj\.cloudflared\config.yml`

```yaml
tunnel: <tunnel-id>
credentials-file: C:\Users\yangj\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8002
  - service: http_status:404
```

## 5. DNS 설정
```powershell
cloudflared tunnel route dns aut-central-backend api.yourdomain.com
```

## 6. 실행
```powershell
# 터미널 1
cd C:\Users\yangj\AUT\central-backend
python run.py

# 터미널 2
cloudflared tunnel run aut-central-backend
```

## 7. 테스트
```
https://api.yourdomain.com/docs
```

## 자동 시작 (선택사항)
```powershell
cloudflared service install
net start cloudflared
```
