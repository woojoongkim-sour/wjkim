-- ============================================================
-- MSP Archive Platform - 시연용 시드 데이터
-- ============================================================

BEGIN;

-- 1. Customers
INSERT INTO customers (id, name, code, description, is_active) VALUES
(1, '한국핀테크 주식회사', 'KFINTECH', '핀테크 결제 플랫폼 운영 고객사. PCI-DSS 준수 필요.', true),
(2, '글로벌이커머스 주식회사', 'GLECOM', '대규모 이커머스 플랫폼. 블랙프라이데이/더블일레븐 대비 필요.', true);

SELECT setval('customers_id_seq', 10);

-- 2. Servers
INSERT INTO servers (id, customer_id, hostname, ip_address, os_type, environment, description, is_active) VALUES
-- 한국핀테크 서버
(1,  1, 'kfin-web-01',    '10.10.1.11', 'Ubuntu 22.04', 'production',  '결제 API 웹서버 #1', true),
(2,  1, 'kfin-web-02',    '10.10.1.12', 'Ubuntu 22.04', 'production',  '결제 API 웹서버 #2', true),
(3,  1, 'kfin-db-master', '10.10.2.10', 'Ubuntu 22.04', 'production',  'PostgreSQL Master', true),
(4,  1, 'kfin-db-slave',  '10.10.2.11', 'Ubuntu 22.04', 'production',  'PostgreSQL Slave (Read Replica)', true),
(5,  1, 'kfin-redis-01',  '10.10.3.10', 'Ubuntu 22.04', 'production',  'Redis 세션/캐시 서버', true),
(6,  1, 'kfin-batch-01',  '10.10.4.10', 'Ubuntu 22.04', 'production',  '정산 배치 서버', true),
(7,  1, 'kfin-mon-01',    '10.10.5.10', 'Ubuntu 22.04', 'management',  'Zabbix/Grafana 모니터링', true),
-- 글로벌이커머스 서버
(8,  2, 'glec-web-01',    '10.20.1.11', 'Rocky Linux 9', 'production', '상품 API 서버 #1', true),
(9,  2, 'glec-web-02',    '10.20.1.12', 'Rocky Linux 9', 'production', '상품 API 서버 #2', true),
(10, 2, 'glec-web-03',    '10.20.1.13', 'Rocky Linux 9', 'production', '주문 API 서버', true),
(11, 2, 'glec-db-01',     '10.20.2.10', 'Rocky Linux 9', 'production', 'MySQL Master', true),
(12, 2, 'glec-es-01',     '10.20.3.10', 'Rocky Linux 9', 'production', 'Elasticsearch 검색엔진', true),
(13, 2, 'glec-cache-01',  '10.20.4.10', 'Rocky Linux 9', 'production', 'Redis 캐시 클러스터', true);

SELECT setval('servers_id_seq', 20);

-- 3. Services
INSERT INTO services (id, customer_id, name, service_type, description, is_active) VALUES
(1, 1, 'Payment Gateway',  'application', '온라인 결제 처리 게이트웨이', true),
(2, 1, 'Settlement Batch',  'batch',       '일/월 정산 배치 프로세스', true),
(3, 1, 'Auth Service',      'application', '인증/토큰 관리 서비스', true),
(4, 1, 'Admin Portal',      'web',         '관리자 포털', true),
(5, 2, 'Product Catalog',   'application', '상품 카탈로그 API', true),
(6, 2, 'Order Processing',  'application', '주문 처리 서비스', true),
(7, 2, 'Search Engine',     'application', 'Elasticsearch 기반 상품 검색', true),
(8, 2, 'CDN/Media',         'infrastructure', '이미지/미디어 CDN 서비스', true);

SELECT setval('services_id_seq', 20);

-- 4. Service-Server Associations
INSERT INTO service_server_association (service_id, server_id) VALUES
(1, 1), (1, 2),
(2, 6),
(3, 1), (3, 2),
(4, 1),
(5, 8), (5, 9),
(6, 10),
(7, 12),
(8, 8), (8, 9);

-- 5. Event Occurrences (한국핀테크 - customer_id=1)
INSERT INTO event_occurrences (id, customer_id, source_system, source_event_id, event_name, severity, host, service, first_seen_at, last_seen_at, current_status, occurrence_count, raw_payload_reference) VALUES
-- CRITICAL: 실 장애 시나리오
(1, 1, 'zabbix', 'ZBX-88401', 'PostgreSQL replication lag exceeds 30s',
   'CRITICAL', 'kfin-db-slave', 'Payment Gateway',
   '2026-04-07 02:15:00+09', '2026-04-08 09:30:00+09', 'OPEN', 12,
   's3://msp-archive/raw/zbx-88401.json'),

(2, 1, 'zabbix', 'ZBX-88455', 'High CPU usage on payment API server (>95%)',
   'CRITICAL', 'kfin-web-01', 'Payment Gateway',
   '2026-04-08 08:05:00+09', '2026-04-08 11:45:00+09', 'ACKNOWLEDGED', 8,
   's3://msp-archive/raw/zbx-88455.json'),

-- HIGH: 주의 필요
(3, 1, 'zabbix', 'ZBX-87920', 'Redis memory usage above 85% threshold',
   'HIGH', 'kfin-redis-01', 'Auth Service',
   '2026-04-06 14:30:00+09', '2026-04-08 10:00:00+09', 'OPEN', 23,
   's3://msp-archive/raw/zbx-87920.json'),

(4, 1, 'zabbix', 'ZBX-88102', 'Settlement batch job failed - retry limit exceeded',
   'HIGH', 'kfin-batch-01', 'Settlement Batch',
   '2026-04-07 23:45:00+09', '2026-04-08 00:15:00+09', 'ACKNOWLEDGED', 3,
   's3://msp-archive/raw/zbx-88102.json'),

(5, 1, 'zabbix', 'ZBX-88510', 'SSL certificate expires in 7 days',
   'HIGH', 'kfin-web-02', 'Payment Gateway',
   '2026-04-08 06:00:00+09', '2026-04-08 06:00:00+09', 'OPEN', 1,
   's3://msp-archive/raw/zbx-88510.json'),

-- MEDIUM
(6, 1, 'zabbix', 'ZBX-87650', 'Disk usage /data partition above 80%',
   'MEDIUM', 'kfin-db-master', 'Payment Gateway',
   '2026-04-05 09:00:00+09', '2026-04-08 09:00:00+09', 'OPEN', 7,
   's3://msp-archive/raw/zbx-87650.json'),

(7, 1, 'zabbix', 'ZBX-88200', 'API response time p99 > 2000ms',
   'MEDIUM', 'kfin-web-01', 'Payment Gateway',
   '2026-04-07 18:30:00+09', '2026-04-08 10:20:00+09', 'OPEN', 15,
   's3://msp-archive/raw/zbx-88200.json'),

(8, 1, 'zabbix', 'ZBX-88350', 'NTP time drift detected (>500ms)',
   'MEDIUM', 'kfin-batch-01', 'Settlement Batch',
   '2026-04-08 01:00:00+09', '2026-04-08 04:00:00+09', 'RESOLVED', 2,
   NULL),

-- LOW
(9, 1, 'zabbix', 'ZBX-86100', 'Swap usage detected on production server',
   'LOW', 'kfin-web-02', 'Payment Gateway',
   '2026-04-03 15:00:00+09', '2026-04-07 15:00:00+09', 'RESOLVED', 5,
   NULL),

(10, 1, 'zabbix', 'ZBX-88050', 'Log rotation failed on monitoring server',
   'LOW', 'kfin-mon-01', NULL,
   '2026-04-07 00:05:00+09', '2026-04-07 00:05:00+09', 'CLOSED', 1,
   NULL),

-- 해결된 이벤트 (오늘 기준)
(11, 1, 'zabbix', 'ZBX-88480', 'Connection pool exhausted',
   'HIGH', 'kfin-web-01', 'Payment Gateway',
   '2026-04-08 07:30:00+09', '2026-04-08 08:00:00+09', 'RESOLVED', 4,
   's3://msp-archive/raw/zbx-88480.json'),

(12, 1, 'zabbix', 'ZBX-88490', 'Abnormal login attempt detected on admin portal',
   'MEDIUM', 'kfin-web-01', 'Admin Portal',
   '2026-04-08 03:22:00+09', '2026-04-08 03:22:00+09', 'RESOLVED', 1,
   's3://msp-archive/raw/zbx-88490.json'),

-- Event Occurrences (글로벌이커머스 - customer_id=2)
(13, 2, 'zabbix', 'ZBX-95010', 'Elasticsearch cluster health RED',
   'CRITICAL', 'glec-es-01', 'Search Engine',
   '2026-04-08 10:00:00+09', '2026-04-08 12:00:00+09', 'OPEN', 6,
   's3://msp-archive/raw/zbx-95010.json'),

(14, 2, 'zabbix', 'ZBX-94800', 'MySQL slow query count spike (>500/min)',
   'HIGH', 'glec-db-01', 'Order Processing',
   '2026-04-07 20:00:00+09', '2026-04-08 11:00:00+09', 'ACKNOWLEDGED', 18,
   's3://msp-archive/raw/zbx-94800.json'),

(15, 2, 'zabbix', 'ZBX-95020', 'Order API 5xx error rate > 5%',
   'CRITICAL', 'glec-web-03', 'Order Processing',
   '2026-04-08 11:15:00+09', '2026-04-08 12:30:00+09', 'OPEN', 3,
   's3://msp-archive/raw/zbx-95020.json'),

(16, 2, 'zabbix', 'ZBX-94500', 'Redis cache hit ratio below 60%',
   'MEDIUM', 'glec-cache-01', 'Product Catalog',
   '2026-04-06 08:00:00+09', '2026-04-08 08:00:00+09', 'OPEN', 10,
   NULL),

(17, 2, 'zabbix', 'ZBX-94900', 'Product image CDN origin 4xx errors spike',
   'MEDIUM', 'glec-web-01', 'CDN/Media',
   '2026-04-08 09:00:00+09', '2026-04-08 10:30:00+09', 'RESOLVED', 2,
   NULL),

(18, 2, 'zabbix', 'ZBX-94600', 'Disk I/O latency above 20ms on DB server',
   'HIGH', 'glec-db-01', 'Order Processing',
   '2026-04-07 16:00:00+09', '2026-04-08 10:00:00+09', 'OPEN', 9,
   's3://msp-archive/raw/zbx-94600.json');

SELECT setval('event_occurrences_id_seq', 30);

-- 6. Event Assessments
INSERT INTO event_assessments (id, occurrence_id, recurrence_score, risk_score, pattern_summary, probable_cause, transfer_to_incident, analyzed_at, analyzer_type) VALUES
(1, 1, 85, 92, '최근 30일 내 DB replication lag 이벤트 12회 반복. 야간 배치 시간대(02:00-04:00) 집중 발생.',
   'WAL 생성량 급증으로 인한 slave 동기화 지연. 대량 UPDATE 쿼리와 정산 배치 동시 실행이 원인으로 추정.',
   true, '2026-04-08 09:35:00+09', 'gpt-4o'),

(2, 2, 45, 88, 'CPU 95% 이상 이벤트 최근 7일간 8회. 오전 08:00-09:00 집중.',
   '결제 API 피크 타임 트래픽 증가. 커넥션 풀 설정 부족 가능성. 최근 배포(v2.3.1)의 메모리 릭 의심.',
   false, '2026-04-08 11:50:00+09', 'gpt-4o'),

(3, 3, 92, 75, 'Redis 메모리 85% 초과 이벤트 23회 반복. 지속적 상승 추세.',
   '세션 TTL 미설정 키 누적 (약 45만개). AUTH 서비스의 토큰 캐시 만료 정책 미흡.',
   false, '2026-04-08 10:05:00+09', 'gpt-4o'),

(4, 4, 30, 80, '정산 배치 실패 최근 3회. 월말/월초 집중.',
   '대량 트랜잭션 처리 시 DB lock timeout 발생. max_retries=3 초과.',
   true, '2026-04-08 00:30:00+09', 'gpt-4o'),

(5, 5, 0, 70, 'SSL 인증서 만료 알림. 최초 발생.',
   'kfin-web-02 서버의 Let''s Encrypt 인증서 자동 갱신 cron 작동 중단. certbot 프로세스 확인 필요.',
   false, '2026-04-08 06:05:00+09', 'gpt-4o'),

(6, 6, 60, 55, '디스크 사용량 80% 이벤트 7회. 주간 약 2% 증가 추세.',
   'WAL 아카이브 파일 정리 미흡. pg_wal 디렉토리 120GB 점유.',
   false, '2026-04-08 09:05:00+09', 'gpt-4o'),

(7, 7, 70, 65, 'API 응답시간 2초 초과 이벤트 15회. 피크 타임 집중.',
   'DB replication lag과 상관관계 높음(r=0.87). slave 읽기 지연이 API 응답에 전파.',
   false, '2026-04-08 10:25:00+09', 'gpt-4o'),

(8, 11, 35, 78, 'Connection pool 고갈 4회 발생. 오전 러시아워 집중.',
   'HikariCP maxPoolSize=20 설정. 동시 트랜잭션 증가 시 대기 발생.',
   false, '2026-04-08 08:05:00+09', 'gpt-4o'),

(9, 13, 40, 95, 'Elasticsearch cluster RED 상태. shard allocation 실패.',
   'glec-es-01 디스크 워터마크 초과로 shard 재배치 불가. 인덱스 lifecycle 정책 미적용.',
   true, '2026-04-08 12:05:00+09', 'gpt-4o'),

(10, 14, 80, 72, 'MySQL slow query 500건/분 초과. 18회 반복.',
   'products 테이블 full scan 쿼리 다수. category_id 인덱스 누락. 최근 스키마 변경(2026-04-05) 이후 발생.',
   false, '2026-04-08 11:05:00+09', 'gpt-4o'),

(11, 15, 20, 90, 'Order API 5xx 에러율 5% 초과. 3회 발생.',
   'Elasticsearch RED 상태로 인한 검색 API timeout → 주문 API cascade failure. Circuit breaker 미설정.',
   true, '2026-04-08 12:35:00+09', 'gpt-4o'),

(12, 18, 65, 68, 'Disk I/O latency 20ms 초과 9회. 야간 백업 시간대 집중.',
   'mysqldump 풀백업과 프로덕션 쿼리 동시 수행. 백업 스케줄 조정 필요.',
   false, '2026-04-08 10:05:00+09', 'gpt-4o');

SELECT setval('event_assessments_id_seq', 20);

-- 7. Event State History
INSERT INTO event_state_history (id, occurrence_id, previous_state, new_state, changed_by, source, description, changed_at) VALUES
-- Event 1: DB replication lag
(1,  1, NULL,           'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-07 02:15:00+09'),
-- Event 2: High CPU
(2,  2, NULL,           'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-08 08:05:00+09'),
(3,  2, 'OPEN',         'ACKNOWLEDGED', '김민수',       'incident_ui',    '담당자 확인. 트래픽 분석 중', '2026-04-08 08:20:00+09'),
-- Event 4: Batch failed
(4,  4, NULL,           'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-07 23:45:00+09'),
(5,  4, 'OPEN',         'ACKNOWLEDGED', '박지현',       'incident_ui',    '배치 로그 확인 중. DBA 협조 요청', '2026-04-08 00:10:00+09'),
-- Event 8: NTP drift (resolved)
(6,  8, NULL,           'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-08 01:00:00+09'),
(7,  8, 'OPEN',         'ACKNOWLEDGED', '이승호',       'incident_ui',    'NTP 서버 동기화 확인', '2026-04-08 01:30:00+09'),
(8,  8, 'ACKNOWLEDGED', 'RESOLVED',     '이승호',       'incident_ui',    'ntpd 재시작으로 해결. chrony 전환 검토.', '2026-04-08 02:00:00+09'),
-- Event 9: Swap usage (resolved)
(9,  9, NULL,           'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-03 15:00:00+09'),
(10, 9, 'OPEN',         'RESOLVED',     '김민수',       'incident_ui',    'JVM heap 조정 후 swap 해소', '2026-04-04 10:00:00+09'),
-- Event 10: Log rotation (closed)
(11, 10, NULL,          'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-07 00:05:00+09'),
(12, 10, 'OPEN',        'RESOLVED',     '박지현',       'incident_ui',    'logrotate 설정 수정', '2026-04-07 09:00:00+09'),
(13, 10, 'RESOLVED',    'CLOSED',       '박지현',       'incident_ui',    '정상 동작 확인. 종료.', '2026-04-07 18:00:00+09'),
-- Event 11: Connection pool (resolved today)
(14, 11, NULL,          'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-08 07:30:00+09'),
(15, 11, 'OPEN',        'ACKNOWLEDGED', '김민수',       'incident_ui',    '커넥션 풀 모니터링 확인', '2026-04-08 07:35:00+09'),
(16, 11, 'ACKNOWLEDGED','RESOLVED',     '김민수',       'incident_ui',    'maxPoolSize 20→50 증설. 재시작 완료.', '2026-04-08 08:00:00+09'),
-- Event 12: Abnormal login (resolved today)
(17, 12, NULL,          'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-08 03:22:00+09'),
(18, 12, 'OPEN',        'RESOLVED',     '이승호',       'incident_ui',    '해외 IP(45.33.xx.xx) 차단 처리. fail2ban 규칙 추가.', '2026-04-08 04:00:00+09'),
-- Event 13: ES cluster RED
(19, 13, NULL,          'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-08 10:00:00+09'),
-- Event 14: MySQL slow query
(20, 14, NULL,          'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-07 20:00:00+09'),
(21, 14, 'OPEN',        'ACKNOWLEDGED', '최영진',       'incident_ui',    'DBA 확인 중. 슬로우 쿼리 로그 분석', '2026-04-08 09:00:00+09'),
-- Event 15: Order API 5xx
(22, 15, NULL,          'OPEN',         'system',       'zabbix_webhook', '이벤트 최초 감지', '2026-04-08 11:15:00+09');

SELECT setval('event_state_history_id_seq', 30);

-- 8. Event Handling Records
INSERT INTO event_handling_records (id, occurrence_id, action_type, action_summary, action_details, actor, executed_at, related_ticket, result_status) VALUES
(1, 2, 'investigation', 'CPU 사용률 분석 및 프로세스 확인',
   'top 명령어 확인 결과 java 프로세스(PID 12847) CPU 94% 점유. GC 로그 확인 시 Full GC 빈번 발생. heap dump 수집 완료.',
   '김민수', '2026-04-08 08:30:00+09', NULL, 'in_progress'),

(2, 2, 'escalation', '개발팀 에스컬레이션',
   'v2.3.1 배포 이후 메모리 릭 의심. 개발팀 heap dump 분석 요청.',
   '김민수', '2026-04-08 09:00:00+09', 'JIRA-KF-1234', 'escalated'),

(3, 4, 'investigation', '배치 실패 원인 분석',
   'settlement_batch.log 확인. ERROR: Lock wait timeout exceeded (innodb_lock_wait_timeout=50). 대량 UPDATE와 배치 동시 실행으로 deadlock 발생.',
   '박지현', '2026-04-08 00:20:00+09', NULL, 'in_progress'),

(4, 4, 'workaround', '배치 수동 재실행',
   '트래픽 감소 시간(04:00) 대기 후 수동 재실행. 정상 완료(소요시간: 23분).',
   '박지현', '2026-04-08 04:30:00+09', 'JIRA-KF-1230', 'completed'),

(5, 8, 'resolve', 'NTP 동기화 복구',
   'ntpd 프로세스 재시작. ntpq -p 확인 결과 offset 0.5ms 이내 정상화. chrony 전환 변경관리 등록.',
   '이승호', '2026-04-08 02:00:00+09', NULL, 'resolved'),

(6, 11, 'resolve', 'Connection Pool 설정 변경',
   'application.yml의 HikariCP maxPoolSize를 20에서 50으로 조정. 서비스 rolling restart 수행. 이후 30분간 모니터링 정상.',
   '김민수', '2026-04-08 07:50:00+09', 'JIRA-KF-1235', 'resolved'),

(7, 12, 'resolve', '비정상 로그인 시도 차단',
   '소스 IP 45.33.32.156 (미국) 에서 admin 계정 brute-force 시도 47회 감지. fail2ban 규칙 추가 및 해당 IP 대역 차단. 2FA 강제 적용 검토 요청.',
   '이승호', '2026-04-08 04:00:00+09', 'JIRA-KF-1231', 'resolved'),

(8, 14, 'investigation', 'Slow query 분석',
   'slow_query_log 분석. SELECT * FROM products WHERE category_name LIKE "%전자%"  → full table scan. category_id 컬럼 인덱스 필요. 2026-04-05 스키마 변경 시 인덱스 누락 확인.',
   '최영진', '2026-04-08 09:30:00+09', 'JIRA-GE-890', 'in_progress'),

(9, 13, 'investigation', 'ES 클러스터 상태 점검',
   'GET _cluster/health → status:red, unassigned_shards:12. 디스크 사용률 92% (watermark.high=90%). 오래된 인덱스 삭제 및 ILM 정책 적용 필요.',
   '최영진', '2026-04-08 10:30:00+09', 'JIRA-GE-891', 'in_progress'),

(10, 1, 'investigation', 'Replication lag 원인 분석',
   'pg_stat_replication 확인. write_lag=32s, flush_lag=35s. WAL 생성량 야간 배치 시간대 급증(평소 대비 5배). slave 디스크 I/O 병목 의심.',
   '박지현', '2026-04-08 09:40:00+09', 'JIRA-KF-1236', 'in_progress');

SELECT setval('event_handling_records_id_seq', 20);

-- 9. Metric Log Evidence
INSERT INTO metric_log_evidence (id, occurrence_id, evidence_type, source, summary, snapshot_reference, collected_at) VALUES
(1, 1, 'metric', 'zabbix', 'DB Replication Lag: 평균 32초, 최대 58초 (최근 24시간)', 's3://msp-archive/evidence/repl-lag-graph.png', '2026-04-08 09:30:00+09'),
(2, 1, 'log', 'postgresql', 'WAL sender 프로세스 로그: streaming 지연 경고 다수 발견', 's3://msp-archive/evidence/pg-wal-sender.log', '2026-04-08 09:30:00+09'),
(3, 2, 'metric', 'zabbix', 'CPU Usage: 95.3% (user: 89%, system: 6.3%). Load Average: 12.5, 10.2, 8.7', 's3://msp-archive/evidence/cpu-usage-graph.png', '2026-04-08 11:45:00+09'),
(4, 2, 'log', 'application', 'GC Log: Full GC 발생 빈도 - 분당 3회. Heap 사용률 97%', 's3://msp-archive/evidence/gc-log-analysis.txt', '2026-04-08 11:45:00+09'),
(5, 3, 'metric', 'zabbix', 'Redis Memory: 6.8GB / 8GB (85%). used_memory_rss: 7.2GB', 's3://msp-archive/evidence/redis-memory.png', '2026-04-08 10:00:00+09'),
(6, 3, 'log', 'redis', 'INFO keyspace: db0:keys=453201,expires=12050. 만료 미설정 키 비율 97%', NULL, '2026-04-08 10:00:00+09'),
(7, 13, 'metric', 'zabbix', 'ES Cluster: status=red, nodes=1, unassigned_shards=12, disk_usage=92%', 's3://msp-archive/evidence/es-cluster-health.png', '2026-04-08 12:00:00+09'),
(8, 14, 'log', 'mysql', 'Slow Query Log 분석: 상위 5개 쿼리 모두 products 테이블 full scan. Avg rows examined: 2.3M', NULL, '2026-04-08 11:00:00+09');

SELECT setval('metric_log_evidence_id_seq', 20);

-- 10. Documents (운영 문서)
INSERT INTO documents (id, customer_id, uuid, title, description, document_type, file_path, file_name, file_size, mime_type, protection_type, processing_status, processing_capability, version, is_active, is_refined, tags) VALUES
(1, 1, 'doc-uuid-001', '결제 시스템 운영 매뉴얼 v3.2', '한국핀테크 결제 게이트웨이 운영 절차서',
   'OPERATION_MANUAL', 's3://msp-archive/docs/kfin-payment-ops-v3.2.pdf', 'kfin-payment-ops-v3.2.pdf',
   2450000, 'application/pdf', 'NONE', 'READY_FOR_SEARCH', 'CHUNKABLE', 3, true, false,
   'payment,gateway,운영,결제,API'),

(2, 1, 'doc-uuid-002', 'PostgreSQL DB 장애 대응 절차서', 'DB 장애 시 단계별 대응 방안 및 복구 절차',
   'EMERGENCY_CONTACT', 's3://msp-archive/docs/kfin-db-emergency.pdf', 'kfin-db-emergency.pdf',
   890000, 'application/pdf', 'NONE', 'READY_FOR_SEARCH', 'CHUNKABLE', 2, true, false,
   'postgresql,replication,장애,복구,failover,DB'),

(3, 1, 'doc-uuid-003', '정산 배치 시스템 구성도 및 운영 가이드', '일/월 정산 프로세스 아키텍처 및 모니터링 가이드',
   'OPERATION_MANUAL', 's3://msp-archive/docs/kfin-settlement-guide.pdf', 'kfin-settlement-guide.pdf',
   1560000, 'application/pdf', 'PASSWORD_PROTECTED', 'BLOCKED_BY_PASSWORD', 'METADATA_ONLY', 1, true, false,
   'settlement,batch,정산,배치'),

(4, 1, 'doc-uuid-004', '서버 점검 절차서 (월간)', '월간 정기 점검 체크리스트 및 절차',
   'INSPECTION_PROCEDURE', 's3://msp-archive/docs/kfin-monthly-check.xlsx', 'kfin-monthly-check.xlsx',
   340000, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'NONE', 'READY_FOR_SEARCH', 'FULLTEXT_EXTRACTABLE', 1, true, false,
   '점검,월간,체크리스트,서버'),

(5, 1, 'doc-uuid-005', 'Redis 운영 가이드 및 메모리 관리', 'Redis 클러스터 운영 및 메모리 최적화 가이드',
   'OPERATION_MANUAL', 's3://msp-archive/docs/kfin-redis-ops.pdf', 'kfin-redis-ops.pdf',
   720000, 'application/pdf', 'NONE', 'READY_FOR_SEARCH', 'CHUNKABLE', 1, true, false,
   'redis,메모리,캐시,세션,TTL'),

(6, 2, 'doc-uuid-006', 'Elasticsearch 클러스터 운영 매뉴얼', 'ES 클러스터 관리, ILM, 장애 복구 절차',
   'OPERATION_MANUAL', 's3://msp-archive/docs/glec-es-ops-manual.pdf', 'glec-es-ops-manual.pdf',
   1800000, 'application/pdf', 'NONE', 'READY_FOR_SEARCH', 'CHUNKABLE', 2, true, false,
   'elasticsearch,검색,cluster,shard,인덱스'),

(7, 2, 'doc-uuid-007', 'MySQL 성능 튜닝 가이드', '슬로우 쿼리 분석 및 인덱스 최적화 가이드',
   'OPERATION_MANUAL', 's3://msp-archive/docs/glec-mysql-tuning.pdf', 'glec-mysql-tuning.pdf',
   950000, 'application/pdf', 'NONE', 'READY_FOR_SEARCH', 'CHUNKABLE', 1, true, false,
   'mysql,slow query,인덱스,튜닝,성능'),

(8, 2, 'doc-uuid-008', '주문 시스템 아키텍처 문서 (기밀)', '주문 처리 마이크로서비스 아키텍처 설계서',
   'CONFIGURATION', 's3://msp-archive/docs/glec-order-arch.pdf', 'glec-order-arch.pdf',
   3200000, 'application/pdf', 'DRM_PROTECTED', 'BLOCKED_BY_DRM', 'METADATA_ONLY', 1, true, false,
   '주문,아키텍처,마이크로서비스');

SELECT setval('documents_id_seq', 20);

-- 11. Document-Server Associations
INSERT INTO document_server_association (document_id, server_id) VALUES
(1, 1), (1, 2),
(2, 3), (2, 4),
(3, 6),
(5, 5),
(6, 12),
(7, 11),
(8, 10);

-- 12. Document-Service Associations
INSERT INTO document_service_association (document_id, service_id) VALUES
(1, 1),
(2, 1),
(3, 2),
(5, 3),
(6, 7),
(7, 6),
(8, 6);

-- 13. Incident Cases (과거 장애 이력)
INSERT INTO incident_cases (id, customer_id, title, description, severity, impact_scope, cause_summary, resolution_summary, occurred_at, resolved_at, related_event_ids, tags, can_be_sanitized, is_sanitized, created_by) VALUES
(1, 1, '결제 API 전면 장애 (2026-03-15)',
   '결제 API 서버 2대 동시 OOM으로 서비스 중단 발생. 약 45분간 결제 불가.',
   'CRITICAL', '전체 결제 서비스 (가맹점 1,200개 영향)',
   'JVM heap 메모리 부족. v2.2.0 배포 시 메모리 설정 누락으로 기본값(256MB) 적용됨.',
   '1) 긴급 서버 재시작 2) JVM heap 4GB로 조정 3) 배포 체크리스트에 메모리 설정 검증 항목 추가',
   '2026-03-15 14:30:00+09', '2026-03-15 15:15:00+09',
   '85010,85011', 'OOM,결제,장애,JVM', true, false, '김민수'),

(2, 1, 'DB Failover 발생 (2026-02-20)',
   'PostgreSQL Master 서버 디스크 장애로 자동 Failover 수행. Slave가 Master로 승격.',
   'CRITICAL', 'DB 의존 전체 서비스 (약 3분간 연결 끊김)',
   'Master 서버 /data 파티션 SSD 불량 섹터 발생. RAID 컨트롤러 경고 무시.',
   '1) Slave→Master 자동 승격 정상 동작 2) SSD 교체 3) RAID 경고 모니터링 임계값 강화',
   '2026-02-20 03:22:00+09', '2026-02-20 03:25:00+09',
   '78200,78201', 'DB,failover,디스크,PostgreSQL', true, true, '박지현'),

(3, 2, 'Elasticsearch 인덱스 손상 (2026-03-28)',
   '상품 검색 인덱스 corruption으로 검색 서비스 장애. 약 2시간 검색 불가.',
   'HIGH', '상품 검색 기능 전체 (매출 영향 추정: ~5천만원)',
   'ES 노드 디스크 full 상태에서 강제 write 시도로 인덱스 손상.',
   '1) 백업 인덱스로 복원 2) 디스크 용량 모니터링 강화 3) ILM 정책 적용으로 자동 인덱스 관리',
   '2026-03-28 11:00:00+09', '2026-03-28 13:10:00+09',
   '92500', 'elasticsearch,인덱스,검색,장애', true, false, '최영진');

SELECT setval('incident_cases_id_seq', 10);

-- 14. Incident-Document Associations
INSERT INTO incident_case_document_association (incident_id, document_id) VALUES
(1, 1),
(2, 2),
(3, 6);

-- 15. Sanitized Knowledge (정제된 지식)
INSERT INTO sanitized_knowledge (id, source_incident_id, title, content, summary, tags, category, status, approved_by, approved_at, usage_count, created_by) VALUES
(1, 2, 'PostgreSQL Failover 대응 절차 (실전)',
   '## PostgreSQL Master-Slave Failover 대응\n\n### 증상\n- Master 서버 접속 불가\n- 애플리케이션 DB 연결 에러 급증\n- Slave replication 중단\n\n### 즉시 조치\n1. pg_isready -h master_ip 로 Master 상태 확인\n2. Slave에서 pg_ctl promote 실행\n3. 애플리케이션 DB endpoint를 Slave IP로 변경\n4. HAProxy/PgBouncer 설정 갱신\n\n### 복구 후 조치\n1. 기존 Master 원인 분석\n2. 신규 Slave 구성 (pg_basebackup)\n3. replication slot 재설정\n4. 모니터링 임계값 검증',
   'PostgreSQL Master 장애 시 Slave 승격 및 서비스 복구 절차. 실제 장애 대응 경험 기반.',
   'postgresql,failover,DB,장애복구,replication', 'database', 'approved', '박지현', '2026-03-01 10:00:00+09', 12, '박지현'),

(2, 1, 'JVM 메모리 관련 장애 체크리스트',
   '## JVM OOM 장애 대응 체크리스트\n\n### 사전 점검\n- [ ] -Xmx, -Xms 설정 확인\n- [ ] GC 로그 활성화 여부\n- [ ] 메모리 모니터링 알림 설정\n\n### 장애 발생 시\n1. jmap -heap <PID> 로 heap 현황 확인\n2. jstat -gcutil <PID> 1000 로 GC 상태 모니터링\n3. 필요시 heap dump: jmap -dump:format=b,file=heap.hprof <PID>\n4. 서비스 재시작 (rolling restart 권장)\n\n### 근본 원인 분석\n- MAT(Memory Analyzer Tool)로 heap dump 분석\n- 메모리 릭 의심 객체 식별\n- 코드 리뷰 및 수정 배포',
   'JVM OOM 장애 사전 점검 및 대응 절차. 결제 시스템 OOM 장애(2026-03-15) 경험 기반.',
   'JVM,OOM,메모리,heap,GC', 'application', 'approved', '김민수', '2026-03-20 14:00:00+09', 8, '김민수');

SELECT setval('sanitized_knowledge_id_seq', 10);

COMMIT;
