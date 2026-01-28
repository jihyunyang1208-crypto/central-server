# central-backend/app/models/financial_data.py
"""
재무 데이터 모델 - PostgreSQL
- 일봉 가격 데이터
- 재무제표 데이터
- 종목 기본 정보
- 공시 정보
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Time, Boolean, Text, Index, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class StockInfo(Base):
    """종목 기본 정보"""
    __tablename__ = "stock_info"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), unique=True, nullable=False, index=True, comment="종목코드 (6자리)")
    name = Column(String(100), nullable=False, comment="종목명")
    market = Column(String(20), nullable=True, comment="시장구분 (KOSPI/KOSDAQ)")
    sector = Column(String(100), nullable=True, comment="업종")
    
    # 메타데이터
    is_active = Column(Boolean, default=True, comment="상장 여부")
    listed_date = Column(Date, nullable=True, comment="상장일")
    delisted_date = Column(Date, nullable=True, comment="상장폐지일")
    
    # 최신 재무 데이터 (비정규화 - 빠른 필터링용)
    latest_revenue = Column(Float, nullable=True, comment="최신 매출액 (억원)")
    latest_operating_profit = Column(Float, nullable=True, comment="최신 영업이익 (억원)")
    latest_operating_margin = Column(Float, nullable=True, index=True, comment="최신 영업이익률 (%)")
    latest_net_profit = Column(Float, nullable=True, comment="최신 당기순이익 (억원)")
    latest_debt_ratio = Column(Float, nullable=True, index=True, comment="최신 부채비율 (%)")
    latest_roe = Column(Float, nullable=True, comment="최신 ROE (%)")
    latest_market_cap = Column(Float, nullable=True, index=True, comment="최신 시가총액 (억원)")
    latest_financial_year = Column(Integer, nullable=True, comment="최신 재무데이터 연도")
    latest_financial_quarter = Column(Integer, nullable=True, comment="최신 재무데이터 분기")
    latest_financial_updated_at = Column(DateTime, nullable=True, comment="재무데이터 갱신일시")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    daily_prices = relationship("DailyPrice", back_populates="stock")
    financial_statements = relationship("FinancialStatement", back_populates="stock")
    disclosures = relationship("Disclosure", back_populates="stock")


class DailyPrice(Base):
    """일봉 가격 데이터"""
    __tablename__ = "daily_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), ForeignKey('stock_info.code'), nullable=False, index=True, comment="종목코드")
    date = Column(Date, nullable=False, index=True, comment="거래일")
    
    # OHLCV
    open = Column(Float, nullable=False, comment="시가")
    high = Column(Float, nullable=False, comment="고가")
    low = Column(Float, nullable=False, comment="저가")
    close = Column(Float, nullable=False, comment="종가")
    volume = Column(Integer, nullable=False, comment="거래량")
    
    # 추가 정보
    change = Column(Float, nullable=True, comment="전일대비")
    change_percent = Column(Float, nullable=True, comment="등락률 (%)")
    
    # 이동평균선 (기술적 지표)
    ma5 = Column(Float, nullable=True, comment="5일 이동평균")
    ma10 = Column(Float, nullable=True, comment="10일 이동평균")
    ma20 = Column(Float, nullable=True, comment="20일 이동평균")
    ma60 = Column(Float, nullable=True, comment="60일 이동평균")
    ma120 = Column(Float, nullable=True, comment="120일 이동평균")
    ma180 = Column(Float, nullable=True, comment="180일 이동평균")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship("StockInfo", back_populates="daily_prices")
    
    # 복합 인덱스 및 유니크 제약
    __table_args__ = (
        Index('ix_daily_prices_code_date', 'code', 'date'),
        UniqueConstraint('code', 'date', name='uq_daily_prices_code_date'),
    )


class FinancialStatement(Base):
    """재무제표 데이터"""
    __tablename__ = "financial_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), ForeignKey('stock_info.code'), nullable=False, index=True, comment="종목코드")
    year = Column(Integer, nullable=False, comment="회계연도")
    quarter = Column(Integer, nullable=False, comment="분기 (1~4, 연간은 0)")
    
    # 손익계산서
    revenue = Column(Float, nullable=True, comment="매출액 (억원)")
    operating_profit = Column(Float, nullable=True, comment="영업이익 (억원)")
    net_profit = Column(Float, nullable=True, comment="당기순이익 (억원)")
    
    # 재무비율
    operating_margin = Column(Float, nullable=True, comment="영업이익률 (%)")
    net_margin = Column(Float, nullable=True, comment="순이익률 (%)")
    roe = Column(Float, nullable=True, comment="ROE (%)")
    roa = Column(Float, nullable=True, comment="ROA (%)")
    
    # 재무상태표
    total_assets = Column(Float, nullable=True, comment="총자산 (억원)")
    total_liabilities = Column(Float, nullable=True, comment="총부채 (억원)")
    total_equity = Column(Float, nullable=True, comment="총자본 (억원)")
    debt_ratio = Column(Float, nullable=True, comment="부채비율 (%)")
    
    # 현금흐름
    operating_cash_flow = Column(Float, nullable=True, comment="영업활동현금흐름 (억원)")
    investing_cash_flow = Column(Float, nullable=True, comment="투자활동현금흐름 (억원)")
    financing_cash_flow = Column(Float, nullable=True, comment="재무활동현금흐름 (억원)")
    
    # 시가총액 (시점 데이터)
    market_cap = Column(Float, nullable=True, comment="시가총액 (억원)")
    
    # 메타데이터
    report_type = Column(String(20), nullable=True, comment="보고서 유형 (정기/반기/분기)")
    source = Column(String(20), default="DART", comment="데이터 출처 (DART/Naver)")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship("StockInfo", back_populates="financial_statements")
    
    # 복합 인덱스 및 유니크 제약
    __table_args__ = (
        Index('ix_financial_statements_code_year_quarter', 'code', 'year', 'quarter'),
        UniqueConstraint('code', 'year', 'quarter', name='uq_financial_statements_code_year_quarter'),
    )


class Disclosure(Base):
    """공시 정보"""
    __tablename__ = "disclosures"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), ForeignKey('stock_info.code'), nullable=False, index=True, comment="종목코드")
    disclosure_date = Column(Date, nullable=False, index=True, comment="공시일")
    disclosure_time = Column(Time, nullable=True, comment="공시시각")
    
    # 공시 내용
    report_name = Column(String(200), nullable=False, comment="공시명")
    submitter = Column(String(100), nullable=True, comment="제출인")
    report_type = Column(String(50), nullable=True, index=True, comment="보고서 유형")
    
    # DART 정보
    reception_number = Column(String(20), nullable=True, unique=True, comment="접수번호 (DART)")
    url = Column(String(500), nullable=True, comment="공시 URL")
    
    # 요약
    summary = Column(Text, nullable=True, comment="공시 요약")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship("StockInfo", back_populates="disclosures")
    
    # 복합 인덱스
    __table_args__ = (
        Index('ix_disclosures_code_date', 'code', 'disclosure_date'),
        Index('ix_disclosures_date', 'disclosure_date'),
    )


class DataCollectionLog(Base):
    """데이터 수집 로그"""
    __tablename__ = "data_collection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_type = Column(String(50), nullable=False, comment="수집 유형 (daily_price/financial_statement/stock_list/disclosure)")
    status = Column(String(20), nullable=False, comment="상태 (success/failed/partial)")
    
    # 수집 통계
    total_count = Column(Integer, default=0, comment="총 처리 건수")
    success_count = Column(Integer, default=0, comment="성공 건수")
    failed_count = Column(Integer, default=0, comment="실패 건수")
    
    # 에러 정보
    error_message = Column(String(500), nullable=True, comment="에러 메시지")
    
    # 수집 기간
    start_date = Column(Date, nullable=True, comment="수집 시작일")
    end_date = Column(Date, nullable=True, comment="수집 종료일")
    
    # 타임스탬프
    started_at = Column(DateTime, nullable=False, comment="수집 시작 시각")
    completed_at = Column(DateTime, nullable=True, comment="수집 완료 시각")
    
    created_at = Column(DateTime, default=datetime.utcnow)
