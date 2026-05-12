#!/usr/bin/env python3
"""Generate 5 sample Korean PDF documents for demo/testing."""

import os
from fpdf import FPDF

FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


DOCUMENTS = [
    {
        "filename": "01_비상연락망_2024.pdf",
        "title": "고객사 비상연락망 (2024년 상반기)",
        "sections": [
            ("1. K금융 비상연락망", """
담당자: 김철수 부장
연락처: 010-1234-5678
이메일: cs.kim@kfinance.co.kr
역할: 인프라 총괄 책임자

담당자: 이영희 차장
연락처: 010-2345-6789
이메일: yh.lee@kfinance.co.kr
역할: DB 운영 담당

담당자: 박민수 대리
연락처: 010-3456-7890
이메일: ms.park@kfinance.co.kr
역할: 네트워크/보안 담당

비상 시 연락 순서: 김철수 → 이영희 → 박민수
24시간 핫라인: 02-1234-0000
"""),
            ("2. G물류 비상연락망", """
담당자: 정대현 팀장
연락처: 010-4567-8901
이메일: dh.jung@glogistics.kr
역할: 시스템 운영 총괄

담당자: 최수진 주임
연락처: 010-5678-9012
이메일: sj.choi@glogistics.kr
역할: 주문/배송 시스템 담당

담당자: 한지민 사원
연락처: 010-6789-0123
이메일: jm.han@glogistics.kr
역할: 모니터링 담당

비상 시 연락 순서: 정대현 → 최수진 → 한지민
업무 시간 외 연락: 070-8888-9999
"""),
            ("3. 에스컬레이션 프로세스", """
Level 1 (15분 이내): 담당 엔지니어 직접 대응
Level 2 (30분 이내): 팀장 보고 및 고객사 연락
Level 3 (1시간 이내): 임원 보고, 비상 대응팀 소집

장애 등급 기준:
- Critical: 서비스 전면 중단 (전체 트래픽 영향)
- Major: 핵심 기능 장애 (결제, 주문 등)
- Minor: 부분 기능 저하 (로그인 지연, 일부 페이지 오류)
"""),
        ],
    },
    {
        "filename": "02_서버_장애_대응_매뉴얼.pdf",
        "title": "서버 장애 대응 매뉴얼 v2.1",
        "sections": [
            ("1. 장애 감지 및 초기 대응", """
1.1 모니터링 알림 확인
- Zabbix 대시보드에서 트리거 상태 확인
- Grafana 알림 채널(Slack #alerts) 확인
- CPU/메모리/디스크 사용률 임계치: 90% 이상 시 경고

1.2 초기 대응 절차
(1) 알림 수신 즉시 담당자 배정 (5분 이내)
(2) 장애 영향 범위 파악: 어떤 서비스, 몇 명의 사용자 영향
(3) 장애 등급 판정 후 에스컬레이션 여부 결정
(4) 고객사 1차 연락 (장애 인지 후 15분 이내)
"""),
            ("2. 장애 유형별 대응", """
2.1 CPU 과부하
- top/htop으로 프로세스 확인
- 비정상 프로세스 kill 또는 서비스 재시작
- 원인 분석: cron job 폭주, 무한루프, 트래픽 급증

2.2 메모리 부족 (OOM)
- dmesg | grep -i oom 으로 OOM 킬러 확인
- 메모리 누수 프로세스 식별: ps aux --sort=-%mem
- 임시 조치: swap 확장 또는 프로세스 재시작
- 근본 조치: 코드 수정 또는 메모리 증설

2.3 디스크 풀
- df -h로 파티션 사용률 확인
- 로그 정리: journalctl --vacuum-size=500M
- 대용량 파일 탐색: du -sh /* | sort -hr | head -20
- /tmp 및 오래된 로그 파일 삭제

2.4 네트워크 장애
- ping/traceroute로 구간 확인
- iptables/firewall 규칙 점검
- DNS 확인: nslookup, dig
- NIC 상태: ip link show, ethtool
"""),
            ("3. 복구 및 사후 조치", """
3.1 서비스 정상화 확인
- 헬스체크 엔드포인트 호출
- 사용자 접속 정상 여부 확인
- 모니터링 알림 해제 확인

3.2 사후 보고서 (RCA) 작성
- 장애 시작/종료 시각
- 영향 범위 (서비스, 사용자 수)
- 근본 원인 (Root Cause)
- 조치 내역 (임시/근본)
- 재발 방지 대책

3.3 고객사 통보
- 장애 보고서 고객사 전달 (24시간 이내)
- 재발 방지 대책 포함
"""),
        ],
    },
    {
        "filename": "03_PostgreSQL_운영_가이드.pdf",
        "title": "PostgreSQL 데이터베이스 운영 가이드",
        "sections": [
            ("1. 일상 점검 항목", """
1.1 매일 점검
- 커넥션 수 확인: SELECT count(*) FROM pg_stat_activity;
- 롱쿼리 확인: 실행 시간 5분 이상 쿼리 모니터링
- Replication lag 확인: SELECT pg_last_xlog_replay_location();
- 디스크 사용량: pg_database_size() 확인
- 백업 완료 여부 확인 (pg_basebackup 로그)

1.2 주간 점검
- VACUUM ANALYZE 실행 상태 확인
- 인덱스 bloat 점검: pgstattuple 확장 활용
- 테이블 사이즈 추이 모니터링
- slow query 로그 분석 (pg_stat_statements)

1.3 월간 점검
- 파라미터 튜닝 검토 (shared_buffers, work_mem 등)
- 파티션 테이블 관리 (오래된 파티션 DROP)
- 통계 정보 갱신: ANALYZE
"""),
            ("2. 백업 및 복구", """
2.1 백업 전략
- Full 백업: pg_basebackup (매일 02:00)
- WAL 아카이빙: archive_mode = on
- 보관 기간: 7일 (로컬) + 30일 (S3)

2.2 복구 절차
(1) 최신 basebackup 복원
(2) recovery.conf 설정 (target_time 지정)
(3) pg_ctl start → recovery 모드 진입
(4) timeline 확인 후 정상 운영 전환

2.3 Point-in-Time Recovery (PITR)
- 특정 시점으로 복구 가능 (WAL 기반)
- recovery_target_time = '2024-01-15 14:30:00'
- 복구 후 데이터 정합성 검증 필수
"""),
            ("3. Failover 절차", """
3.1 자동 Failover (Patroni 기반)
- Primary 장애 감지: 30초 이내
- Standby 자동 승격 (promote)
- DNS/VIP 전환: 5초 이내
- 애플리케이션 재연결: 커넥션 풀 refresh

3.2 수동 Failover
(1) Primary 상태 확인: pg_isready -h primary
(2) Standby에서 승격: pg_ctl promote
(3) 클라이언트 연결 전환 (DNS 변경 또는 pgbouncer 설정)
(4) 기존 Primary를 Standby로 재구성

3.3 Split-brain 방지
- fencing 메커니즘 필수 (STONITH)
- quorum 기반 의사결정
- 네트워크 파티션 시 Primary 자동 shutdown
"""),
        ],
    },
    {
        "filename": "04_K금융_결제시스템_아키텍처.pdf",
        "title": "K금융 결제 시스템 아키텍처 문서 v3.0",
        "sections": [
            ("1. 시스템 개요", """
K금융 결제 시스템은 마이크로서비스 아키텍처 기반으로 구성되며,
일 평균 트랜잭션 150만 건을 처리합니다.

주요 구성 요소:
- Payment Gateway: 외부 PG사 연동 (KG이니시스, 토스페이먼츠)
- Order Service: 주문 생성 및 상태 관리
- Settlement Service: 정산 배치 처리 (매일 새벽 3시)
- Notification Service: 결제 알림 (SMS, Push, Email)

기술 스택:
- Backend: Java 17 + Spring Boot 3.2
- Database: PostgreSQL 15 (Primary-Standby)
- Cache: Redis Cluster (6노드)
- Message Queue: Apache Kafka (3 broker)
- Container: Kubernetes (EKS)
"""),
            ("2. 결제 처리 흐름", """
2.1 결제 요청
사용자 → 프론트엔드 → API Gateway → Payment Service

2.2 처리 단계
(1) 결제 요청 수신 및 유효성 검증
(2) 중복 결제 방지 (Idempotency Key 확인)
(3) PG사 결제 승인 요청
(4) 결제 결과 DB 저장
(5) 이벤트 발행 (Kafka: payment.completed)
(6) 알림 서비스로 결제 완료 통보

2.3 결제 취소/환불
- 당일 취소: PG사 즉시 취소 API 호출
- 익일 이후: 환불 프로세스 (영업일 기준 3-5일)
- 부분 환불: 원거래 금액 내에서 분할 환불 가능

2.4 정산
- T+1 정산: 전일 거래 기준 다음 영업일 정산
- 정산 금액 = 결제 금액 - PG 수수료 - 부가세
- 정산 파일: CSV 형식 (계좌번호, 금액, 거래일시)
"""),
            ("3. 장애 대응 시나리오", """
3.1 PG사 연동 장애
- Circuit Breaker 패턴 적용 (Resilience4j)
- Fallback: 대체 PG사로 자동 전환
- 재시도: 최대 3회, exponential backoff

3.2 DB 장애
- Read Replica 활용 (조회 분산)
- Primary 장애 시 자동 Failover (Patroni)
- 결제 상태 불일치 시: 배치 정합성 체크 (매 10분)

3.3 Kafka 장애
- 프로듀서: 로컬 큐에 임시 저장 후 재전송
- 컨슈머: offset 관리 및 exactly-once 보장
- 클러스터 장애: 최소 2개 broker 가용 시 정상 운영

3.4 SLA
- 가용성: 99.95% (월간 다운타임 21분 이내)
- 응답 시간: P95 < 500ms
- 처리량: 초당 500 TPS 이상
"""),
        ],
    },
    {
        "filename": "05_모니터링_알림_설정_가이드.pdf",
        "title": "Zabbix/Grafana 모니터링 알림 설정 가이드",
        "sections": [
            ("1. 모니터링 대상 및 임계치", """
1.1 서버 리소스
| 항목 | Warning | Critical |
| CPU 사용률 | 80% 이상 5분 지속 | 95% 이상 2분 지속 |
| 메모리 사용률 | 85% 이상 | 95% 이상 |
| 디스크 사용률 | 80% | 90% |
| 네트워크 대역폭 | 70% | 90% |

1.2 애플리케이션
| 항목 | Warning | Critical |
| 응답 시간 (P95) | 1초 초과 | 3초 초과 |
| 에러율 | 1% 초과 | 5% 초과 |
| 큐 적체 | 1000건 초과 | 5000건 초과 |
| DB 커넥션 풀 | 80% 사용 | 95% 사용 |

1.3 비즈니스 메트릭
| 항목 | Warning | Critical |
| 결제 실패율 | 3% 초과 | 10% 초과 |
| 주문 처리 지연 | 5분 초과 | 15분 초과 |
| 배치 미완료 | 예정 시각 +30분 | 예정 시각 +2시간 |
"""),
            ("2. Zabbix 트리거 설정", """
2.1 호스트 그룹
- KFinance-Production: K금융 운영 서버 (12대)
- GLogistics-Production: G물류 운영 서버 (8대)
- Shared-Infra: 공유 인프라 (모니터링, 로그, CI/CD)

2.2 주요 트리거 예시
Trigger: CPU High
Expression: {host:system.cpu.util.avg(5m)}>80
Severity: Warning
Action: Slack #monitoring 알림

Trigger: Disk Full Soon
Expression: {host:vfs.fs.size[/,pfree].last()}<10
Severity: Critical
Action: Slack + PagerDuty + SMS

Trigger: Service Down
Expression: {host:net.tcp.service[http,,8080].last()}=0
Severity: Critical
Action: 즉시 에스컬레이션 + 자동 재시작 시도
"""),
            ("3. Grafana 대시보드 구성", """
3.1 Overview 대시보드
- 전체 서비스 상태 (Green/Yellow/Red)
- 최근 1시간 에러율 추이
- 현재 활성 알림 목록
- 고객사별 트래픽 분포

3.2 서비스별 대시보드
- Request Rate (RPM)
- Response Time (P50, P95, P99)
- Error Rate by status code
- 인스턴스별 리소스 사용률

3.3 알림 채널 설정
- Slack: #monitoring-alerts (전체), #kfin-alerts (K금융 전용)
- PagerDuty: Critical 등급만 연동
- Email: 일일 리포트 (매일 09:00)
- SMS: Critical 장애 시 담당자 직접 통보
"""),
            ("4. 온콜 로테이션", """
4.1 스케줄
- 평일 주간 (09:00-18:00): 담당 엔지니어 2인
- 평일 야간 (18:00-09:00): 온콜 1인
- 주말/공휴일: 온콜 1인 + 백업 1인

4.2 현재 로테이션 (2024년 1월)
- Week 1: 김철수 (Primary) / 이영희 (Backup)
- Week 2: 박민수 (Primary) / 김철수 (Backup)
- Week 3: 이영희 (Primary) / 박민수 (Backup)
- Week 4: 김철수 (Primary) / 이영희 (Backup)

4.3 온콜 규칙
- 알림 수신 후 10분 이내 응답 필수
- 30분 이내 미응답 시 자동 에스컬레이션
- 온콜 중 음주 금지, 이동 시 노트북 지참
"""),
        ],
    },
]


def create_pdf(doc_info: dict):
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_font("Nanum", "", FONT_PATH)
    if os.path.exists(FONT_BOLD_PATH):
        pdf.add_font("NanumBold", "", FONT_BOLD_PATH)
    else:
        pdf.add_font("NanumBold", "", FONT_PATH)

    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("NanumBold", "", 18)
    pdf.set_x(15)
    pdf.multi_cell(w=180, h=12, text=doc_info["title"], align="C")
    pdf.ln(20)
    pdf.set_font("Nanum", "", 11)
    pdf.set_x(15)
    pdf.multi_cell(w=180, h=8, text="MSP Archive Platform - 시연용 샘플 문서", align="C")
    pdf.set_x(15)
    pdf.multi_cell(w=180, h=8, text="작성일: 2024-01-15", align="C")
    pdf.set_x(15)
    pdf.multi_cell(w=180, h=8, text="문서 분류: 내부용", align="C")

    for section_title, content in doc_info["sections"]:
        pdf.add_page()
        pdf.set_font("NanumBold", "", 13)
        pdf.set_x(15)
        pdf.multi_cell(w=180, h=8, text=section_title)
        pdf.ln(2)
        pdf.set_font("Nanum", "", 9)
        for line in content.strip().split("\n"):
            if len(line) > 75:
                line = line[:75]
            pdf.set_x(15)
            pdf.multi_cell(w=180, h=5, text=line)

    # Save
    output_path = os.path.join(OUTPUT_DIR, doc_info["filename"])
    pdf.output(output_path)
    return output_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {len(DOCUMENTS)} sample PDFs...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    for doc in DOCUMENTS:
        path = create_pdf(doc)
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✓ {doc['filename']} ({size_kb:.1f} KB)")

    print(f"\nDone! {len(DOCUMENTS)} files created in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
