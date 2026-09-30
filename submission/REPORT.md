# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Phạm Đình Hải
- **MSSV:** 2A202602482
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/haikunn11/K4-L3-DAY13-PhamDinhHai-2A202602482-Monitoring-LLMOps.git
- **Commit SHA cuối:** `58c3b2a477e055c5fbad12b8e63f85e5601e26d1`
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602482`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt điểm tuyệt đối; đầy đủ schema, correlation ID propagation, context enrichment và PII scrubbing |
| `validate_dashboard.py` | Hợp lệ 6/6 panel | Hợp lệ 6/6 panel | Dashboard contract YAML hoàn toàn hợp lệ |
| `pytest` | 22 passed | 25 passed | Đã bổ sung unit test cho CCCD, Credit Card, Passport; 100% test pass |
| Số traces hợp lệ | 10 traces | 10 traces | Đã tạo và truyền correlation ID nối kết nối trace Langfuse |
| Số PII leak | 0 | 0 | Không còn rò rỉ PII; email, phone VN, cccd, thẻ đều được che bằng [REDACTED_*] |
| Latency P95 / TTFT P95 | 1153.0ms / 50.0ms | 1191.0ms / 50.0ms | Đo lường thực tế từ workload với API đã hoàn thiện middleware & logger |
| Retrieval success rate | 100% | 100% | Toàn bộ 10/10 requests ở baseline đều retrieval thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, trước mỗi request gọi `clear_contextvars()` để tránh rò rỉ ngữ cảnh giữa các request. Kiểm tra header `x-request-id`: nếu có thì sử dụng, nếu không có hoặc rỗng thì tự động sinh mới theo định dạng `req-<8-char-hex>` (dùng `f"req-{uuid.uuid4().hex[:8]}"`). Sau đó bind vào structlog contextvars (`bind_contextvars(correlation_id=correlation_id)`), gán vào `request.state.correlation_id`, và trả về trong response header `x-request-id` cùng `x-response-time-ms`. Correlation ID này cũng được truyền xuyên suốt vào `LabAgent.run` để đưa vào metadata của Langfuse trace.
- **Các metadata được ghi vào structured log:** Mỗi log record chứa các trường bắt buộc và mở rộng: `ts` (ISO UTC timestamp), `level` (info/error), `service` (api), `event` (request_received, response_sent, request_failed), `correlation_id` (mã theo dõi duy nhất), `user_id_hash` (SHA256 băm 12 ký tự của user_id), `session_id`, `feature` (qa/summary), `model` (claude-sonnet-4-5), `env` (dev), cùng các metrics hiệu năng ở response_sent: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `payload` preview đã được scrub PII.
- **Cách bảo đảm PII được scrub trước khi ghi:** Hàm `scrub_event` trong `app/logging_config.py` được đăng ký vào pipeline `structlog.processors` ngay trước `JsonlFileProcessor()` và `JSONRenderer()`. Bộ lọc `scrub_event` duyệt đệ quy qua tất cả các trường dữ liệu chuỗi (ngoại trừ các ID hệ thống), áp dụng regex patterns từ `app/pii.py` (Email, Phone VN các định dạng, CCCD 12 số, Thẻ ngân hàng 16 số, Passport) để thay thế bằng `[REDACTED_<TYPE>]` trước khi bất kỳ dữ liệu nào được tuần tự hóa ra JSON hoặc ghi vào file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt điểm tuyệt đối 100/100: không thiếu trường bắt buộc, không thiếu enrichment, có đủ 10 correlation IDs riêng biệt, và phát hiện 0 rò rỉ PII. Kiểm tra trực tiếp file `data/logs.jsonl` thấy các thông tin như email `student@vinuni.edu.vn`, số điện thoại `0987654321` và thẻ tín dụng đều đã được chuyển đổi thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`. Bộ unit test `pytest tests/test_pii.py` đạt 100% pass với 5 test case kiểm thử toàn diện.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project được tạo riêng trên Langfuse Cloud có tên `day13-k4-l3b-2A202602482`. Các traces được gửi trực tiếp thông qua cặp API keys cá nhân cấu hình trong `.env`. Mỗi trace có metadata chứa `user_id_hash`, `session_id`, `environment="dev"`, và `correlation_id` khớp từng ký tự với log trong `data/logs.jsonl` được tạo ra trên máy local của tôi.
- **Cấu trúc root/retrieval/generation observations:** Mỗi trace bắt đầu bằng Root observation tên `day13-agent-request` / span `lab-agent-run` (type `AGENT`), bên dưới gồm 2 child observations:
  1. `retrieval` (type `RETRIEVER`): đo thời gian tìm kiếm tài liệu trong corpus, ghi nhận metadata `matched_key`, `doc_count`.
  2. `generation` (type `GENERATION`): đo thời gian sinh câu trả lời của mô hình LLM, ghi nhận `model="claude-sonnet-4-5"`, prompt version được liên kết, `usage_details` (`input`, `output`, `total`), `cost_details`, và `ttft_ms`.
- **Cách nối trace với log:** Sử dụng mã theo dõi duy nhất `correlation_id` (định dạng `req-<8-char-hex>`). Trong log file `data/logs.jsonl`, correlation_id xuất hiện ở tất cả các event `request_received`, `response_sent`, `request_failed`. Trong Langfuse trace, correlation_id được truyền thông qua context `propagate_attributes(metadata={"correlation_id": correlation_id})`, cho phép tìm kiếm trực tiếp trace tương ứng từ bất kỳ dòng log nào.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, mang các label ban đầu `baseline` và `production`. Prompt template: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`.
- **Version/label candidate:** Version 2, mang label `candidate`. Prompt template bổ sung chỉ dẫn trả lời ngắn gọn, chuẩn xác dựa trên context được cung cấp.
- **Trace ID của mỗi version:**
  - Version 1 (baseline/production): Trace ID `a76d79f89214f13cc02ccae1f556cc46` (Obs ID: `2ae3699f8a7d5f57`), `90ee067962cd2457cfa5f6e09ebe8dc0`.
  - Version 2 (candidate/promoted): Trace ID `090a8f42009ff5b99f7b186e1e9d31ab` (Obs ID: `19e3db890d3c7925`).
- **Cách promote và rollback `production`:**
  - *Promote:* Chuyển nhãn `production` sang Version 2 (`client.update_prompt(name="day13-chat", version=2, new_labels=["candidate", "production"])`), cập nhật Version 1 chỉ còn label `["baseline"]`. Khi đó API production tự động nạp prompt v2 từ Langfuse Cloud mà không cần sửa hay redeploy code.
  - *Rollback:* Khi cần rollback về v1, chuyển lại nhãn `production` về Version 1 (`client.update_prompt(name="day13-chat", version=1, new_labels=["baseline", "production"])`) và gán lại Version 2 là `["candidate"]`. Hệ thống lập tức hoàn nguyên về prompt v1 ổn định ban đầu.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng dashboard runtime hiển thị dữ liệu thực tế từ `data/logs.jsonl` tại endpoint `/dashboard` và file config `config/dashboard.yaml`, bao gồm đầy đủ 6 panel:
  1. *Latency percentiles & TTFT*: hiển thị Latency P50, P95, P99 và TTFT P95 (đơn vị: ms, threshold P95 $\le$ 3000ms).
  2. *Request traffic*: số lượng request và tần suất requests/phút (đơn vị: requests_per_minute, threshold $\ge$ 1 req/min).
  3. *Error rate & retrieval success*: tỷ lệ lỗi (%) và tỷ lệ thành công của retrieval (%) (đơn vị: percent, threshold error rate $\le$ 2%, retrieval success $\ge$ 90%).
  4. *Cost over time*: tổng chi phí và chi phí trung bình theo request (đơn vị: USD, threshold total $\le$ $2.50).
  5. *Input & Output tokens*: tổng số token input và token output (đơn vị: tokens, threshold sum $\le$ 50,000 tokens).
  6. *Quality proxy*: điểm chất lượng heuristic trung bình theo thang 0.0 - 1.0 (đơn vị: score_0_to_1, threshold mean $\ge$ 0.75).
- **SLO và lý do chọn:** SLO chính được xác định là `fast_successful_requests` với mục tiêu: 99.5% request đạt kết quả thành công (`event == "response_sent"`) và có độ trễ `latency_ms <= 3000ms` trong cửa sổ đánh giá 28 ngày (`window: 28d`). Lý do chọn: Người dùng cuối trong ứng dụng tương tác hội thoại trực tiếp yêu cầu phản hồi nhanh dưới 3 giây; nếu trễ quá 3 giây sẽ gây trải nghiệm chờ đợi tiêu cực và giảm tỷ lệ tương tác.
- **Cách tính error budget:** Với target SLO là 99.5% trong cửa sổ 28 ngày, Error Budget được phép là $100\% - 99.5\% = 0.5\%$. Điều này có nghĩa là nếu hệ thống tiếp nhận 10,000 requests trong 28 ngày, tối đa chỉ có $10,000 \times 0.5\% = 50$ requests được phép bị lỗi (HTTP 500) hoặc có độ trễ vượt quá ngưỡng 3000ms. Nếu số request vi phạm vượt quá 50, Error Budget sẽ bị cạn kiệt (exhausted), đội ngũ phát triển phải dừng release tính năng mới để tập trung vá lỗi và tối ưu hiệu năng.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95` (Severity: warning, Duration: 5m, Channel: Slack `#k4-l3b-alerts`): Cảnh báo khi Latency P95 > 3000ms kéo dài 5 phút. Runbook tại `docs/alerts.md#alert-1` hướng dẫn kiểm tra panel Latency, lọc log tìm `correlation_id` chậm, mở Langfuse trace so sánh span retrieval và generation để cô lập điểm nghẽn, sau đó rollback prompt hoặc hạ tải.
  2. `HighErrorRate` (Severity: critical, Duration: 2m, Channel: Slack `#k4-l3b-alerts`): Cảnh báo khi tỷ lệ lỗi `error_rate_pct > 2%` trong 2 phút. Runbook tại `docs/alerts.md#alert-2` yêu cầu kiểm tra bảng phân loại `error_type`, trích xuất log `request_failed` và mở stack trace để xử lý sự cố sập dịch vụ phụ thuộc hoặc bật fallback.
  3. `LowRetrievalSuccessRate` (Severity: critical, Duration: 3m, Channel: Slack `#k4-l3b-alerts`): Cảnh báo khi `retrieval_success_rate_pct < 90%` trong 3 phút. Runbook tại `docs/alerts.md#alert-3` chỉ dẫn kiểm tra kết nối vector store, tắt scenario lỗi timeout nếu đang test, và kích hoạt corpus fallback.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30T03:55:32Z – 2026-09-30T03:55:48Z
- **Triệu chứng từ metrics:** Quan sát trên Panel Latency của Dashboard và endpoint `/metrics`, độ trễ Latency P95 và P99 tăng đột biến từ baseline ~390ms lên 4157ms, vi phạm nghiêm trọng ngưỡng SLO 3000ms và vượt ngưỡng cảnh báo của challenge (`latency_threshold_ms: 2000`). Trong khi đó, Error rate vẫn giữ ở mức 0% và chi phí không bị spike, chứng minh triệu chứng cốt lõi của sự cố là suy giảm độ trễ phản hồi (Tail Latency Degradation).
- **Log line và correlation ID liên quan:**
  - Event `request_received`: `correlation_id: req-544a6be3`, `session_id: k4-l3b-challenge-s03`, `feature: monitoring`, `ts: 2026-09-30T03:55:32.789918Z`.
  - Event `response_sent`: `correlation_id: req-544a6be3`, `session_id: k4-l3b-challenge-s03`, `latency_ms: 4157`, `ttft_ms: 50`, `quality_score: 0.8`, `tool_name: retrieval`, `tool_success: true`, `ts: 2026-09-30T03:55:37.432090Z`.
- **Trace ID và span gây ảnh hưởng:**
  - Request có correlation ID `req-544a6be3` gắn với trace chứa các spans: `lab-agent-run` (Agent), `retrieval` (Retriever), `generation` (Generation).
  - So sánh thời gian thực thi: Span `retrieval` bị chậm nghiêm trọng, tiêu tốn hơn 2500ms (chiếm hơn 60% tổng thời gian request), trong khi span `generation` chỉ tiêu tốn 151ms.
- **Root cause:** Lớp tìm kiếm ngữ cảnh RAG vector search bị suy giảm hiệu năng nghiêm trọng (bị kích hoạt kịch bản sự cố `rag_slow`), dẫn đến mỗi lời gọi hàm `retrieve()` bị trễ thêm 2.5 giây (2500ms).
- **Fix action:**
  - Ngay lập tức gọi lệnh tắt kịch bản sự cố via API: `POST /incidents/rag_slow/disable` (hoặc chạy `python scripts/inject_incident.py --disable`).
  - Trong môi trường production thực tế: Khởi động lại hoặc scale-out cụm vector database / indexer, bổ sung Redis cache cho các embedding vector truy vấn phổ biến, hoặc chuyển tạm thời sang fallback keyword search.
- **Preventive measure:**
  - Kích hoạt alert `HighLatencyP95` đã cấu hình trong `config/alert_rules.yaml` (bắn cảnh báo khi P95 > 3000ms trong 5m tới Slack `#k4-l3b-alerts`).
  - Thiết lập timeout tối đa cho bước retrieval (ví dụ: hard timeout 1500ms) kèm cơ chế circuit breaker: nếu vector store không phản hồi trong 1.5s thì fallback sang tài liệu cache/mặc định thay vì bắt người dùng chờ quá lâu.
  - Xây dựng performance regression test định kỳ trên pipeline CI/CD trước khi release phiên bản mới.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định thực hiện PII scrubbing đệ quy (`scrub_event`) ngay trong pipeline của Structlog trước khi render JSON và ghi ra file/gửi qua trace. Lý do: Bảo đảm nguyên tắc Data Privacy by Design, ngăn chặn triệt để nguy cơ rò rỉ thông tin cá nhân (Email, Phone VN, CCCD, Thẻ) xuống ổ cứng hay dịch vụ giám sát bên thứ ba.
- **Một lỗi/blocker đã gặp:** Khi bắt đầu, lệnh load test trả về `correlation_id: MISSING` và validator chấm 30/100 do middleware chưa bind contextvars và request header. Đồng thời, cấu hình Langfuse SDK v4 ban đầu thiếu child observations cho retriever và generation khiến cây trace không phân tách được thời gian giữa các bước.
- **Cách tìm nguyên nhân và xử lý:** Đọc kỹ hướng dẫn kiến trúc, triển khai `clear_contextvars()` và `bind_contextvars()` trong middleware để truyền correlation ID xuyên suốt. Thêm `@observe` cho `retrieve` và `FakeLLM.generate` với đầy đủ metadata, model, usage, cost để tạo cây quan sát 3 tầng hoàn chỉnh.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - *Metrics*: Cung cấp góc nhìn vĩ mô (High-level bird's-eye view) để phát hiện "Hệ thống có vấn đề gì và bắt đầu từ lúc nào?".
  - *Logs*: Thu hẹp phạm vi xuống mức vi mô (Micro-level) thông qua `correlation_id` để biết "Request cụ thể nào bị ảnh hưởng và có thông điệp gì?".
  - *Traces*: Cung cấp phân tích chi tiết từng micro-step bên trong request đó thông qua waterfall spans để chỉ ra "Bước nào (span) chạy chậm hoặc sinh lỗi?".
  - Nhờ chuỗi 3 mắt xích này, kỹ sư có thể tìm ra Root cause dựa trên 100% bằng chứng kiểm chứng được.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Prompt trong LLM tương đương với mã nguồn/logic nghiệp vụ. Quản lý prompt theo version và label (`production`, `candidate`) cho phép deploy và rollback tức thì khi prompt mới gây hồi quy (regression) như sinh token dài bất thường, tăng chi phí hoặc giảm chất lượng mà không phải build/deploy lại container.
  - Quản lý Token & Cost bảo đảm ngân sách vận hành không bị cạn kiệt do prompt injection hay loop.
  - SLO & Error budget thiết lập cam kết chất lượng với người dùng, đồng thời làm cơ sở quyết định tốc độ release tính năng mới.
- **Điều quan trọng nhất đã học:** Học được tư duy thực chiến về Full Observability cho hệ thống AI Agent: không thể vận hành AI dựa trên "cảm tính", mà phải có hệ thống đo lường minh bạch từ logging an toàn, tracing chi tiết đến dashboard cảnh báo chủ động.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Các metric hiện tại chủ yếu phục vụ ứng dụng đơn lẻ; trong production quy mô lớn cần tích hợp thêm OpenTelemetry Collector phân tán và hệ thống vector database cluster thực thụ.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
