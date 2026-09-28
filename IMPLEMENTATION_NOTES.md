# Implementation Notes — Day 11 Guardrails / HITL / Responsible AI

## Phạm vi đã hoàn thành

### Checkpoint 2 — Input và output guardrails

- Chuẩn hóa Unicode NFKC, xóa zero-width characters và gom khoảng trắng trước khi kiểm tra.
- Phát hiện nhiều mẫu prompt injection bằng regex, gồm ignore/disregard instructions,
  system prompt, reveal prompt, role-play và unrestricted-agent patterns.
- Hỗ trợ tín hiệu tấn công bằng tiếng Anh và tiếng Việt.
- Topic filter theo allowlist/blocklist, có word boundary để giảm false positive và hỗ trợ
  câu tiếng Việt có dấu.
- `InputGuardrailPlugin` chặn request trước model và cập nhật thống kê.
- `content_filter` phát hiện/redact email, số điện thoại Việt Nam, CMND/CCCD, API key,
  password và internal database host.
- `OutputGuardrailPlugin` thay nội dung nhạy cảm bằng `[REDACTED]`; LLM-as-Judge vẫn là
  phần optional và mặc định không bật trong production pipeline.

### Checkpoint 3 — Defense-in-depth pipeline

- Sliding-window rate limiter riêng theo `user_id`.
- Audit logger có correlation ID, input/output, layer quyết định, trạng thái blocked,
  timestamp và latency.
- Monitoring tính block rate, rate-limit hits, judge fail rate và sinh alerts theo ngưỡng.
- Plugin order: Rate Limiter → Input Guardrail → Output Guardrail.
- Egress policy chỉ cho HTTPS tới hostname VinBank nằm trong allowlist và chặn payload
  chứa PII/secret; hostname được so khớp chính xác để tránh domain giả mạo.
- Assignment suite chạy ổn định, không cần gọi LLM, và sinh:
  - `outputs/results.json`
  - `outputs/audit_log.json`
  - `outputs/metrics.json`
- Kết quả suite:
  - Safe queries: 5, blocked: 0
  - Attack queries: 7, blocked: 7
  - Rate-limit requests: 12, blocked: 2
  - Edge cases: 3

### Checkpoint 4 — Red team

- Viết 5 prompt theo các kỹ thuật:
  1. Completion / fill-in-the-blank
  2. Translation / reformatting
  3. Hypothetical / creative writing
  4. Confirmation / side-channel
  5. Multi-step / gradual escalation
- Chạy cùng 5 prompt trên Red và Red Advance bằng OpenAI `gpt-4o-mini`.
- Red leak: 5/5; Red Advance leak: 0/5.
- Kết quả phù hợp điều kiện bắt buộc và bonus B1; không đạt bonus B2, và rubric chỉ cho
  chọn một trong B1/B2.
- Sinh:
  - `outputs/unsafe_attack_result.json`
  - `outputs/guards_attack_result.json`
  - `outputs/attack_results.json`

### Checkpoint 5 — Kiểm tra và báo cáo

- `pytest tests/smoke -q`: 6 passed.
- `pytest tests/public -q`: 10 passed.
- Python compile check cho `src/` và `scripts/`: passed.
- `scripts/grade.py`: `technical_failure=false`.
- Grader sinh:
  - `outputs/grade_report.json`
  - `outputs/lab_report.md`

## Ghi chú vận hành

- Không commit `.env` hoặc API key.
- Chạy lệnh từ thư mục gốc repository.
- Trên Windows nên dùng `python -m pytest` thay vì gọi trực tiếp `pytest.exe`.
- Nếu terminal gặp lỗi mã hóa tiếng Việt, chạy `$env:PYTHONUTF8='1'` trước lệnh Python.
- `src/hitl/`, `src/testing/`, LLM-as-Judge và NeMo là phần tham khảo/optional theo đề,
  không thuộc phần bắt buộc đã triển khai.

## Web demo (làm lại từ project nguyên bản)

- Xóa UI một file cũ và tách thành app nhiều trang bằng `st.navigation`.
- Không thêm API chat-history vào core; `OpenAIRunner.chat()` giữ đúng contract nguyên bản.
- Blue chatbot dùng trực tiếp `create_blue_agent(build_production_plugins(...))`, gọi
  OpenRouter thật sau consent và giữ các plugin trong session để demo rate limiting.
- Blue chatbot dùng `AuditLogPlugin` + `MonitoringAlert` trong session để hiển thị
  correlation ID, decision, layer, latency, block rate và alert; dữ liệu được redact
  trước khi render hoặc tải xuống.
- CP2 chạy trực tiếp `detect_injection`, `topic_filter`, `content_filter` và toàn bộ 10 case
  PII; 8 case hallucination được ghi rõ là dataset đối chiếu cho Judge optional.
- CP3 demo `RateLimitPlugin`, `is_egress_allowed`, results và monitoring artifacts.
- CP3 có thể chạy lại toàn bộ `run_assignment_suite()` trên web và sinh đúng ba artifact
  phòng thủ theo checkpoint.
- CP3 có tab Audit & monitoring đọc `audit_log.json` và `metrics.json`, hỗ trợ lọc
  BLOCK/ALLOW và trình bày lớp đã đưa ra quyết định.
- HITL demo policy đã có trong `agents/security_boundary.py`; `src/hitl/hitl.py` được ghi rõ
  là optional/TODO, không trình bày như phần đã triển khai.
- CP4 hiển thị đủ 5 attack trên Red và Red Advance từ artifact thật, đồng thời có Live
  attack runner để chạy một prompt tùy chỉnh hoặc toàn bộ 5 prompt qua provider trong `.env`.
  Kết quả live không tự ghi đè artifact; mọi chuỗi nhạy cảm được redact trước khi render.
- CP4 có thao tác riêng để chạy đúng 10 lượt Red + Red Advance và gọi
  `save_attack_results()` nhằm cập nhật artifact chấm bài.
- CP5 kiểm tra artifact, packaging, schema và cung cấp bản preview/download đã redact.
- CP5 gọi trực tiếp `scripts/grade.py` từ nút self-check, chạy public tests và tự sinh report.
- Giữ `BLUE_MODEL=liquid/lfm-2.5-2.6b` đúng rubric; runtime dùng route OpenRouter
  `liquid/lfm-2.5-2.6b:free` của cùng model để demo live hoạt động.
- Thêm light theme native tại `.streamlit/config.toml` và headless multipage tests tại
  `tests/ui/test_streamlit_app.py`.
- Lệnh chạy: `streamlit run streamlit_app.py` từ thư mục gốc repository.
