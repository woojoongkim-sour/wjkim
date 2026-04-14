#!/usr/bin/env python3
"""Seed MinIO with demo data for MSP Archive Platform"""

import io
import json
import os
from datetime import datetime
from io import BytesIO

import boto3
from PIL import Image, ImageDraw
from fpdf import FPDF
from openpyxl import Workbook

# Config
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET = "msp-archive"


def create_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def _find_cjk_font():
    # Try to locate a CJK font (e.g., NanumGothic, Noto Sans CJK)
    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]
    for d in font_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith(".ttf") or f.lower().endswith(".ttc"):
                    if any(x in f.lower() for x in ["nanum", "noto", "wqy", "cnsc"]):
                        return os.path.join(root, f)
    return None


def _make_pdf(title, paragraphs, use_cjk):
    pdf = FPDF()
    font_path = _find_cjk_font()
    if font_path:
        try:
            pdf.add_font("CJK", "", font_path, uni=True)
            pdf.set_font("CJK", "", 12)
            use_cjk = True
        except Exception:
            pdf.set_font("Arial", "", 12)
            use_cjk = False
    else:
        pdf.set_font("Arial", "", 12)
        use_cjk = False

    # Create 2 pages per document to ensure 2-3 pages per spec
    blocks = paragraphs
    for idx, block in enumerate(blocks):
        pdf.add_page()
        header = f"{title} - Part {idx+1}" if len(blocks) > 1 else title
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, header, ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.ln(4)
        text = block
        # Korean-friendly or english text
        pdf.multi_cell(0, 10, text)
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        data = bytes(raw)
    else:
        data = str(raw).encode("utf-8")
    return data


def generate_documents():
    files = {}

    # 8 PDFs (docs/...). We'll generate Korean-like content if font is available,
    # otherwise fall back to English.
    use_korean = _find_cjk_font() is not None

    docs = {
        "docs/kfin-payment-ops-v3.2.pdf": [
            "결제 시스템 운영 매뉴얼 – API 엔드포인트, 장애 대응, 모니터링, 결제 흐름",
            "API endpoints: /payments, /refunds, 결제 흐름: 카트 -> 결제 -> 정산",
            "장애 대응: 로깅, 알림, 재시도 정책, 장애 시나리오별 대응 프로세스",
        ],
        "docs/kfin-db-emergency.pdf": [
            "PostgreSQL DB 장애 대응 절차서—Failover 및 Recovery",
            "Failover 절차: primary-대기 서버 전환, 자동/수동 승격",
            "Replication 복구 및 백업/복원: PITR, WAL 파일 관리",
        ],
        "docs/kfin-settlement-guide.pdf": [
            "정산 배치 시스템 구성도",
            "배치 스케줄: 매 시각 정산 잡 실행, 에러 처리 흐름",
            "정산 프로세스: 데이터 흐름, 트랜잭션 관리, 롤백 시나리오",
        ],
        # Excel will be created separately
        "docs/kfin-monthly-check.xlsx": None,
        "docs/kfin-redis-ops.pdf": [
            "Redis 운영 가이드: 메모리 관리, TTL 정책, 세션 관리, 모니터링",
            "메모리 관리: maxmemory 정책, eviction 전략",
        ],
        "docs/glec-es-ops-manual.pdf": [
            "Elasticsearch 클러스터 운영 매뉴얼: ILM 정책, 샤드 관리, 장애 복구",
        ],
        "docs/glec-mysql-tuning.pdf": [
            "MySQL 성능 튜닝 가이드: 인덱스 최적화, slow query 분석, 쿼리 튜닝",
        ],
        "docs/glec-order-arch.pdf": [
            "주문 시스템 아키텍처 문서: 마이크로서비스 구성도, API 설계, 데이터 흐름",
        ],
    }

    from_text = {
        0: [
            "This document provides operational guidance for MSP Archive's payment subsystem.",
        ],
    }

    for path, blocks in docs.items():
        if path.endswith('.xlsx'):
            continue
        if blocks is None:
            continue
        if not use_korean:
            blocks_to_render = [
                os.path.basename(path) + " - English summary",
                "API endpoints, failure handling, monitoring, and payment flow."
            ]
        else:
            blocks_to_render = blocks
        data = _make_pdf(os.path.basename(path), blocks_to_render, use_korean)
        files[path] = data

    # Create the Excel file (docs/kfin-monthly-check.xlsx)
    wb = Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet(title="Sheet1", index=0)
    ws.append(["점검항목", "대상서버", "점검방법", "정상기준", "결과"])
    items = [
        ["CPU 사용률", "kfin-web-01", "snmp/psutil", "<75%", "양호"],
        ["메모리 사용률", "kfin-db-master", "vmstat", ">80%", "경고"],
        ["디스크 I/O", "kfin-redis-01", "iostat", "<20ms", "양호"],
    ]
    for it in items:
        ws.append(it)

    excel_bytes = BytesIO()
    wb.save(excel_bytes)
    files["docs/kfin-monthly-check.xlsx"] = excel_bytes.getvalue()

    return files


def generate_raw_payloads():
    now = datetime.utcnow()
    entries = [
        ("zbx-88401.json", "PostgreSQL replication lag", "kfin-db-slave", "CRITICAL"),
        ("zbx-88455.json", "High CPU usage", "kfin-web-01", "CRITICAL"),
        ("zbx-87920.json", "Redis memory >85%", "kfin-redis-01", "HIGH"),
        ("zbx-88102.json", "Settlement batch failed", "kfin-batch-01", "HIGH"),
        ("zbx-88510.json", "SSL cert expires", "kfin-web-02", "HIGH"),
        ("zbx-87650.json", "Disk usage /data >80%", "kfin-db-master", "MEDIUM"),
        ("zbx-88200.json", "API response time p99 >2000ms", "kfin-web-01", "MEDIUM"),
        ("zbx-88480.json", "Connection pool exhausted", "kfin-web-01", "HIGH"),
        ("zbx-88490.json", "Abnormal login attempt", "kfin-web-01", "MEDIUM"),
        ("zbx-95010.json", "ES cluster health RED", "glec-es-01", "CRITICAL"),
        ("zbx-94800.json", "MySQL slow query spike", "glec-db-01", "HIGH"),
        ("zbx-95020.json", "Order API 5xx >5%", "glec-web-03", "CRITICAL"),
        ("zbx-94600.json", "Disk I/O latency >20ms", "glec-db-01", "HIGH"),
    ]
    payloads = {}
    for idx, (filename, trigger_name, host, sev) in enumerate(entries):
        payload = {
            "event_id": f"evt-{88401 + idx}",
            "trigger_id": f"trg-{88401 + idx}",
            "trigger_name": trigger_name,
            "trigger_severity": sev,
            "host_name": host,
            "host_ip": f"10.0.{idx % 255}.{idx % 254}",
            "item_name": trigger_name,
            "item_value": f"value-{idx}",
            "event_date": now.strftime("%Y-%m-%d"),
            "event_time": now.strftime("%H:%M:%S"),
            "event_status": "PROBLEM",
            "trigger_description": f"Seed event: {trigger_name}",
            "tags": ["seed", host],
        }
        key = f"raw/{filename}"
        payloads[key] = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return payloads


def generate_evidence():
    files = {}
    # 1) repl-lag-graph.png
    def _make_line_img(vals, title):
        w, h = 640, 480
        img = Image.new("RGB", (w, h), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # axes
        draw.line((40, h - 40, w - 10, h - 40), fill=(0, 0, 0), width=2)
        draw.line((40, h - 40, 40, 10), fill=(0, 0, 0), width=2)
        # plot
        max_v = max(vals) if vals else 1
        pts = []
        for i, v in enumerate(vals):
            x = 40 + int((w - 60) * i / max(1, len(vals) - 1))
            y = h - 40 - int((h - 60) * (v / max_v))
            pts.append((x, y))
        if len(pts) >= 2:
            draw.line(pts, fill=(0, 0, 255), width=2)
        draw.text((45, 12), title, fill=(0, 0, 0))
        out = BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    files["evidence/repl-lag-graph.png"] = _make_line_img([5, 8, 15, 40, 90, 200, 350], "Replication Lag")

    # 3) cpu-usage-graph.png
    files["evidence/cpu-usage-graph.png"] = _make_line_img([20, 25, 40, 60, 75, 85, 95], "CPU Usage %")

    # 5) redis-memory.png
    files["evidence/redis-memory.png"] = _make_line_img([50, 55, 60, 68, 72, 80, 85], "Redis Memory %")

    # 6) es-cluster-health.png with gradient green->red
    w, h = 640, 480
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # axes
    draw.line((40, h - 40, w - 10, h - 40), fill=(0, 0, 0), width=2)
    draw.line((40, h - 40, 40, 10), fill=(0, 0, 0), width=2)
    pts = []
    days = 15
    for i in range(days):
        x = 40 + int((w - 60) * i / (days - 1))
        # gradient path from green to red as a simple proxy for health deterioration
        t = i / (days - 1)
        r = int(0 + 255 * t)
        g = int(255 - 255 * t)
        b = 0
        y = h - 40 - int((h - 60) * (1 - t) * 0.6)
        pts.append((x, y))
        draw.line([(x, y)], fill=(r, g, b))
    draw.text((45, 12), "ES Cluster Health (green->red)", fill=(0, 0, 0))
    out = BytesIO()
    img.save(out, format="PNG")
    files["evidence/es-cluster-health.png"] = out.getvalue()

    # 2) pg-wal-sender.log
    log_lines = []
    base = now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for i in range(32):
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_lines.append(f"{ts} [walsender] INFO: wal sender event {i} writing WAL segment {i:04d}")
    files["evidence/pg-wal-sender.log"] = "\n".join(log_lines).encode("utf-8")

    # 4) gc-log-analysis.txt
    gc_lines = [
        "GC round 1: Minor GC completed in 12ms",
        "GC round 2: Major GC triggered, reclaimed 120MB",
        "GC analysis: allocation rate stable, heap occupancy 65% -> 60%",
        "GC optimizations: tuned -XX:+UseG1GC, -XX:MaxGCPauseMs=200",
    ]
    gc_lines.extend([f"Line {i+5}: dummy GC event detail" for i in range(16)])
    files["evidence/gc-log-analysis.txt"] = "\n".join(gc_lines).encode("utf-8")

    return files


def upload_all(client, files):
    uploaded = []
    for key, data in files.items():
        client.put_object(Bucket=BUCKET, Key=key, Body=data)
        uploaded.append(key)
    return uploaded


def main():
    client = create_s3_client()
    # Ensure bucket exists (it should per task)
    try:
        client.head_bucket(Bucket=BUCKET)
    except Exception:
        client.create_bucket(Bucket=BUCKET)

    files = {}
    print("Generating documents...")
    docs = generate_documents()
    files.update(docs)

    print("Generating raw payloads...")
    raws = generate_raw_payloads()
    files.update(raws)

    print("Generating evidence files...")
    ev = generate_evidence()
    files.update(ev)

    print("Uploading all files to MinIO...")
    uploaded = upload_all(client, files)
    print(f"Uploaded {len(uploaded)} objects to s3://{BUCKET}")
    for k in uploaded:
        print(f" - {k}")

    # Quick verification: list objects in bucket and count
    resp = client.list_objects_v2(Bucket=BUCKET)
    count = resp.get('KeyCount', 0)
    print(f"Verification: bucket contains {count} objects.")


if __name__ == "__main__":
    main()
