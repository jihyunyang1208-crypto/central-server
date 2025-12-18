# Cloudflare Tunnel 설정 가이드

## 개요
Cloudflare Tunnel을 사용하여 로컬 중앙 백엔드 서버를 인터넷에 안전하게 노출합니다.

**장점:**
- ✅ 완전 무료
- ✅ 고정 URL (영구)
- ✅ HTTPS 자동
- ✅ DDoS 보호
- ✅ 포트포워딩 불필요

---

## 1단계: Cloudflare 계정 생성

### 회원가입
1. https://dash.cloudflare.com/sign-up 접속
2. 이메일로 무료 가입
3. 이메일 인증

---

## 2단계: cloudflared 설치

### Windows 설치

**방법 1: 직접 다운로드 (권장)**
```powershell
# 1. 다운로드
# https://github.com/cloudflare/cloudflared/releases/latest
# cloudflared-windows-amd64.exe 다운로드

# 2. 파일명 변경
Rename-Item cloudflared-windows-amd64.exe cloudflared.exe

# 3. PATH에 추가 (선택사항)
# C:\cloudflared\ 폴더에 저장 후 환경 변수 PATH에 추가
```

**방법 2: Chocolatey**
```powershell
choco install cloudflared
```

### 설치 확인
```powershell
cloudflared --version
# 출력: cloudflared version 2024.x.x
```

---

## 3단계: Cloudflare 로그인

```powershell
cloudflared tunnel login
```

**결과:**
- 브라우저가 자동으로 열림
- Cloudflare 계정으로 로그인
- 권한 승인
- 인증 완료 메시지 확인

---

## 4단계: 터널 생성

```powershell
# 터널 생성
cloudflared tunnel create aut-central-backend

# 출력 예시:
# Tunnel credentials written to C:\Users\yangj\.cloudflared\<tunnel-id>.json
# Created tunnel aut-central-backend with id <tunnel-id>
```

**중요:** `<tunnel-id>`를 복사해두세요!

---

## 5단계: 설정 파일 생성

### config.yml 생성

**위치:** `C:\Users\yangj\.cloudflared\config.yml`

```yaml
tunnel: <tunnel-id>  # 4단계에서 받은 ID
credentials-file: C:\Users\yangj\.cloudflared\<tunnel-id>.json

ingress:
  # 중앙 백엔드
  - hostname: api.yourdomain.com
    service: http://localhost:8002
  
  # 기본 규칙 (필수)
  - service: http_status:404
```

**파일 생성 명령:**
```powershell
# .cloudflared 폴더로 이동
cd C:\Users\yangj\.cloudflared

# 메모장으로 config.yml 생성
notepad config.yml
```

---

## 6단계: DNS 설정

### 옵션 A: 무료 도메인 사용 (추천)

**Freenom에서 무료 도메인 받기:**
1. https://www.freenom.com 접속
2. 원하는 도메인 검색 (예: `myaut.tk`)
3. 무료 등록 (12개월)

**Cloudflare에 도메인 추가:**
```powershell
# DNS 레코드 생성
cloudflared tunnel route dns aut-central-backend api.myaut.tk
```

### 옵션 B: 본인 도메인 사용

이미 도메인이 있다면:
```powershell
cloudflared tunnel route dns aut-central-backend api.yourdomain.com
```

---

## 7단계: 터널 실행

```powershell
# 터미널 1: 중앙 백엔드 실행
cd C:\Users\yangj\AUT\central-backend
python run.py

# 터미널 2: Cloudflare Tunnel 실행
cloudflared tunnel run aut-central-backend
```

**성공 메시지:**
```
INF Connection registered connIndex=0
INF Connection registered connIndex=1
INF Connection registered connIndex=2
INF Connection registered connIndex=3
```

---

## 8단계: 테스트

### API 문서 접속
```
https://api.myaut.tk/docs
```

### 회원가입 테스트
```bash
curl -X POST https://api.myaut.tk/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

---

## 9단계: 자동 시작 설정

### Windows 서비스로 등록

```powershell
# 관리자 권한으로 실행
cloudflared service install
```

**서비스 관리:**
```powershell
# 시작
net start cloudflared

# 중지
net stop cloudflared

# 상태 확인
sc query cloudflared
```

---

## 10단계: 프론트엔드 연동

### .env 파일 업데이트

**AUT-dashboard/.env**
```env
VITE_CENTRAL_API_URL=https://api.myaut.tk
```

**코드 수정**
```typescript
// src/config.ts
export const API_URL = import.meta.env.VITE_CENTRAL_API_URL || 'http://localhost:8002';

// API 호출
fetch(`${API_URL}/api/v1/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
```

---

## 문제 해결

### 터널이 연결되지 않음
```powershell
# 터널 목록 확인
cloudflared tunnel list

# 터널 삭제 후 재생성
cloudflared tunnel delete aut-central-backend
cloudflared tunnel create aut-central-backend
```

### DNS가 작동하지 않음
```powershell
# DNS 레코드 확인
nslookup api.myaut.tk

# DNS 레코드 재생성
cloudflared tunnel route dns aut-central-backend api.myaut.tk
```

### 502 Bad Gateway
- 중앙 백엔드가 실행 중인지 확인
- 포트 8002가 맞는지 확인
- config.yml의 service URL 확인

---

## 보안 설정

### CORS 업데이트

**central-backend/app/core/config.py**
```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://api.myaut.tk",  # Cloudflare Tunnel URL 추가
]
```

### Rate Limiting
```python
# 이미 설정되어 있음
@limiter.limit("10/minute")
def register(...):
    ...
```

---

## 비용

**완전 무료!**
- Cloudflare Tunnel: 무료
- 무료 도메인 (Freenom): 무료
- HTTPS 인증서: 무료
- DDoS 보호: 무료

---

## 다음 단계

1. ✅ Cloudflare Tunnel 설정 완료
2. ✅ 고정 URL로 서비스 시작
3. 📊 사용자 피드백 수집
4. 🚀 사용자 100명+ 시 AWS 이전 고려
