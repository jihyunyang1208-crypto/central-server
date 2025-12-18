# Central Backend Server

중앙 백엔드 서버 - 사용자 인증, 구독 관리, 커미션 관리

## 기능

- **사용자 관리**: 회원가입, 로그인, JWT 인증 (Argon2 해싱)
- **구독 관리**: 플랜 선택, 구독 시작/취소, 업그레이드
- **커미션 관리**: 추천 시스템, 커미션 발생/지급, 30일 홀드백

## 설치

```bash
cd central-backend
pip install -r requirements.txt
```

## 환경 설정

### 필수 환경 변수 설정

`.env` 파일이 이미 생성되어 있습니다. 다음 항목들을 확인하세요:

#### 🔐 SECRET_KEY (이미 설정됨)

JWT 토큰 서명 키가 자동으로 생성되어 있습니다.

**새로운 키가 필요한 경우:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

생성된 키를 `.env` 파일의 `SECRET_KEY`에 복사하세요.

> ⚠️ **주의**: 
> - 이 키는 절대 공유하거나 Git에 커밋하지 마세요
> - 프로덕션에서는 더 긴 키 사용 권장: `secrets.token_urlsafe(64)`

#### 🗄️ DATABASE_URL (이미 설정됨)

PostgreSQL 연결 정보 (AutoTrader와 동일한 DB):

```env
DATABASE_URL=postgresql+psycopg2://postgres:0509@localhost:5432/aut_db
```

#### 🔑 MASTER_ENCRYPTION_KEY (이미 설정됨)

브로커 자격증명 암호화 키 (AutoTrader와 동일):

```env
MASTER_ENCRYPTION_KEY=QfsUAr74Kyhsvy2Fev08EHQF6LpBGAwbjwwvGUpe1qc=
```

#### 🌐 서버 설정 (이미 설정됨)

```env
PORT=8002  # AutoTrader(8000), Trading API(8001)와 충돌 방지
```

## 실행

```bash
python run.py
```

또는

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## API 문서

서버 실행 후:
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc
- **헬스 체크**: http://localhost:8002/health

## 주요 엔드포인트

### 인증
- `POST /api/v1/auth/register` - 회원가입 (추천 코드 지원)
- `POST /api/v1/auth/login` - 로그인 (JWT 발급)
- `POST /api/v1/auth/refresh` - 토큰 갱신

### 구독
- `GET /api/v1/subscriptions/plans` - 플랜 목록
- `GET /api/v1/subscriptions/me` - 내 구독 정보
- `POST /api/v1/subscriptions/subscribe` - 구독 시작
- `PUT /api/v1/subscriptions/upgrade` - 플랜 변경
- `POST /api/v1/subscriptions/cancel` - 구독 취소

### 커미션
- `GET /api/v1/commissions/me` - 커미션 내역
- `GET /api/v1/commissions/stats` - 커미션 통계
- `POST /api/v1/commissions/request-payout` - 지급 요청

## 초기 데이터 설정

### 구독 플랜 생성

PostgreSQL에 접속하여 플랜 데이터 삽입:

```sql
-- 구독 플랜 생성
INSERT INTO subscription_plans (name, display_name, price_monthly, price_yearly, max_conditions, max_stocks, is_active)
VALUES 
('FREE', '무료', 0, 0, 3, 10, true),
('BASIC', '베이직', 29000, 290000, 10, 50, true),
('PRO', '프로', 99000, 990000, NULL, NULL, true);

-- 커미션 비율 설정
INSERT INTO commission_rates (event_type, rate_percentage, is_active, description)
VALUES 
('SIGNUP', 10.0, true, '신규 가입 시 10% 커미션'),
('RENEWAL', 5.0, true, '구독 갱신 시 5% 커미션'),
('UPGRADE', 15.0, true, '플랜 업그레이드 시 15% 커미션');
```

## 데이터베이스

PostgreSQL 사용 (AutoTrader와 동일한 DB)

**테이블:**
- `users` - 사용자
- `subscriptions` - 구독
- `subscription_plans` - 구독 플랜 (마스터)
- `referrals` - 추천 관계
- `commissions` - 커미션
- `commission_rates` - 커미션 비율 (마스터)

## 아키텍처

```
central-backend/
├── app/
│   ├── models/          # DB 모델
│   ├── api/             # API 라우터
│   ├── core/            # 핵심 로직 (보안, 설정)
│   ├── services/        # 비즈니스 로직
│   ├── schemas/         # Pydantic 스키마
│   └── main.py          # FastAPI 앱
├── requirements.txt
├── .env                 # 환경 변수 (Git 제외)
├── .env.example         # 환경 변수 예시
└── run.py               # 서버 실행
```

## 보안 주의사항

1. **SECRET_KEY**: 절대 공유하지 말 것
2. **MASTER_ENCRYPTION_KEY**: AutoTrader와 동일한 키 사용
3. **DATABASE_URL**: 비밀번호 노출 주의
4. **`.env` 파일**: `.gitignore`에 추가 (이미 설정됨)

## 문제 해결

### 포트 충돌
```
ERROR: [Errno 10048] error while attempting to bind on address
```
→ `.env`에서 `PORT` 변경 (예: 8002)

### 모듈 없음 오류
```
ModuleNotFoundError: No module named 'pydantic_settings'
```
→ `pip install -r requirements.txt` 재실행

### DB 연결 실패
```
could not connect to server
```
→ PostgreSQL 서버 실행 확인 및 `DATABASE_URL` 검증



# 구독 플랜
## ✨ Standard/Pro 플랜 맞춤형 트레이딩 기능 설계 (로컬 백엔드 워커)

제안된 Standard 플랜(자동 즉시 매매)과 Pro 플랜(커스텀 기술적 매매)의 기능을 로컬 백엔드 워커에서 구분하여 실행할 수 있도록 설계하겠습니다. 이 설계는 중앙 서버의 **구독 검증 응답**(`plan_type`, `max_strategy_count`)을 기반으로 기능 제한 및 해제를 관리합니다.

### 1\. 로컬 백엔드 워커 아키텍처 개요

로컬 백엔드 워커는 **매수 모듈**과 **매도 모듈**을 분리하고, 각 모듈 내에서 **플랜에 따른 로직 분기**를 통해 기능을 제한합니다.

| 모듈 | Standard Plan (Tier 2) | Pro Plan (Tier 3) |
| :---: | :---: | :---: |
| **매수 모듈** | **자동 즉시 매수** (시장가/지정가 즉시 주문) | **커스텀 기술적 매수** (추가 기술적 지표 검토 후 매수) |
| **매도 모듈** | **단순 청산** (손익률/시간 기반) | **커스텀 기술적 매도** (조건검색식 활용 청산) |
| **전략 개수 제한** | 5개 이하 | 20개 이상 (제한 없음 또는 고가 제한) |

-----

### 2\. 매수 모듈 설계: 진입 로직 분기

매수 모듈은 키움 조건검색식으로 종목이 포착되었을 때 실행됩니다.

#### A. Standard Plan (자동 즉시 매수)

| 항목 | 상세 로직 |
| :--- | :--- |
| **목표** | 포착된 종목을 **가장 빠르게** 매수하여 전략의 기계적 실행 보장. |
| **실행 로직** | 1. 조건식 포착 $\rightarrow$ 2. 잔고/예수금 확인 $\rightarrow$ 3. **즉시 시장가 주문** 또는 **사전 설정된 지정가 주문** 실행 $\rightarrow$ 4. 매도 감시 리스트에 종목 추가. |
| **사용자 설정** | 매수 비중(예수금 대비 % 또는 정액), 매수 호가 유형(시장가/지정가). |

#### B. Pro Plan (커스텀 기술적 매수)

| 항목 | 상세 로직 |
| :--- | :--- |
| **목표** | 조건식 포착 후 **사용자 정의 추가 기술 분석**을 거쳐 매수 타이밍 최적화. |
| **실행 로직** | 1. 조건식 포착 $\rightarrow$ 2. **추가 지표 검증:** (예: 포착 후 5분봉 RSI가 70 이하로 떨어질 때까지 대기) $\rightarrow$ 3. 매수 조건 충족 시 주문 실행 $\rightarrow$ 4. 매도 감시 리스트에 종목 추가. |
| **사용자 설정** | **추가 진입 지표** (RSI, MACD, 볼린저 밴드 등), 지표 값 설정, 대기 시간 설정. |

-----

### 3\. 매도 모듈 설계: 청산 로직 분기

매도 모듈은 현재 보유 종목을 실시간으로 감시하며 실행됩니다.

#### A. Standard Plan (단순 청산)

| 항목 | 상세 로직 |
| :--- | :--- |
| **목표** | 감정에 영향받지 않는 **기계적 손절/익절**로 리스크 관리. |
| **실행 로직** | 1. 보유 종목의 **실시간 수익률** 감시. $\rightarrow$ 2. 수익률이 사전 설정된 **익절/손절 비율**에 도달 $\rightarrow$ 3. 즉시 **시장가 매도** 주문 실행. |
| **사용자 설정** | 익절 비율(예: +3.0%), 손절 비율(예: -1.5%), 보유 시간 제한(예: 매수 후 24시간). |

#### B. Pro Plan (커스텀 기술적 매도)

| 항목 | 상세 로직 |
| :--- | :--- |
| **목표** | 기술적 분석을 통한 **최적의 추세 이탈 시점**에 청산하여 수익 극대화. |
| **실행 로직** | 1. **'기술적 매도 조건식'** 실시간 감시 (키움 API). $\rightarrow$ 2. 매도 조건식에 **보유 종목이 포착**되는지 교차 검증 (방법 1). $\rightarrow$ 3. 조건 충족 시 주문 실행. |
| **사용자 설정** | **키움 조건식 ID** 입력 (매도 전용), 분할 매도 비율, 청산 호가 유형. |

-----

### 4\. 로컬 백엔드 워커의 기능 분기 관리

로컬 백엔드 워커는 중앙 서버의 `/verify` API 응답을 받아 자신의 기능을 제한합니다.

| API 응답 필드 | 값 | 기능 활성화 |
| :--- | :--- | :--- |
| `plan_type` | `"Standard"` | 즉시 매수/매도, 단순 청산 로직만 활성화. |
| `plan_type` | `"Pro"` | 커스텀 기술적 매수/매도, 단순 청산 로직 모두 활성화. |
| `max_strategy_count` | `5` 또는 `20` | UI 및 워커 내부에서 실행 가능한 **조건식 감시 프로세스의 개수**를 제한. |

워커 내부의 Python 코드는 `plan_type` 변수를 체크하는 `if-else` 구문을 사용하여 기능을 명확히 분리합니다.

```python
# 로컬 백엔드 워커 (Python Trade Executor)

def process_signal(signal_data, current_plan_type):
    # 1. 매수 모듈 실행
    if current_plan_type == "Pro" and signal_data.has_custom_buy_logic:
        execute_custom_technical_buy(signal_data)
    else:
        execute_standard_immediate_buy(signal_data)

def monitor_holding_stock(stock_data, current_plan_type):
    # 2. 매도 모듈 실행
    if current_plan_type == "Pro" and stock_data.has_sell_condition_id:
        # Pro: 사용자 정의 매도 조건식(키움 API) 감시 로직 실행
        execute_technical_sell(stock_data)
    else:
        # Standard: 단순 손익률/시간 청산 로직 실행
        execute_standard_profit_loss_sell(stock_data)
```

이 설계는 플랜별로 제공되는 가치를 명확히 분리하여 **Pro 플랜의 프리미엄 가치**를 부여하고, 중앙 서버의 인증을 통해 서비스 라이선스를 강력하게 관리합니다.