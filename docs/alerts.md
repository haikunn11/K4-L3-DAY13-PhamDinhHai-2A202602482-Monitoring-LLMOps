# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn bình thường trước khi nhận được phản hồi từ AI Assistant.
- Ba bước kiểm tra đầu tiên:
  1. Mở Panel Latency trên Dashboard để xác định khoảng thời gian latency P95 bắt đầu vượt 3000ms và kiểm tra TTFT P95.
  2. Lọc `data/logs.jsonl` trong khoảng thời gian đó, lấy một `correlation_id` có `latency_ms` cao bất thường.
  3. Mở Langfuse trace cùng `correlation_id`, so sánh thời gian của child span `retrieval` và `generation` để xác định bước chậm (RAG hay LLM generate).
- Mitigation tạm thời: Nếu do RAG vector store quá tải/chậm, khởi động lại cache hoặc chuyển sang fallback search; nếu do Prompt mới sinh câu trả lời quá dài, thực hiện rollback prompt label `production` về version trước; nếu do incident practice thì tắt via API `/incidents/rag_slow/disable`.
- Owner: `student-2A202602482`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `2m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỷ lệ lỗi toàn hệ thống `error_rate_pct` (guardrail max 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` kéo dài trong 2 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc không nhận được câu trả lời từ API.
- Ba bước kiểm tra đầu tiên:
  1. Mở Panel Errors trên Dashboard để quan sát tỷ lệ lỗi và xem `error_breakdown` (phân loại lỗi theo `error_type`).
  2. Lọc file `data/logs.jsonl` tìm các log event `request_failed` gần nhất, trích xuất `correlation_id` và trường `payload.detail`.
  3. Tìm kiếm trace ID tương ứng trên Langfuse để xem stack trace và span phát sinh ngoại lệ.
- Mitigation tạm thời: Kiểm tra tính sẵn sàng của các dịch vụ phụ thuộc (vector store, model API); bật circuit breaker hoặc trả về fallback response; restart app nếu rò rỉ bộ nhớ.
- Owner: `student-2A202602482`

## Alert 3

- Tên: `LowRetrievalSuccessRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỷ lệ thành công của Retrieval `retrieval_success_rate_pct` (guardrail min 90%)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` trong 3 phút
- Ảnh hưởng tới người dùng: AI Assistant không tìm được tài liệu ngữ cảnh phù hợp, dẫn đến câu trả lời thiếu chính xác, hallucination hoặc lỗi timeout.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Panel Errors trên Dashboard, đối chiếu chỉ số `tool_success_rate_pct`.
  2. Lọc log sự kiện `request_failed` có `tool_name="retrieval"` và `tool_success=false` trong `data/logs.jsonl`.
  3. Mở Langfuse trace tìm span `retrieval` bị đánh dấu level `ERROR` với message `Vector store timeout`.
- Mitigation tạm thời: Kiểm tra kết nối tới cơ sở dữ liệu vector; nếu do incident test `tool_fail` thì gọi `/incidents/tool_fail/disable`; kích hoạt cơ chế fallback sang tài liệu mặc định (`CORPUS fallback`).
- Owner: `student-2A202602482`
