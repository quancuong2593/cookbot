# Chi phí dự án

**Ngày ước tính:** 2026-07-20. Giá AWS và Claude API có thể đổi bất cứ lúc nào — coi các con số dưới đây là tham khảo, không phải cam kết. Trước khi tin tưởng hoàn toàn, đối chiếu lại với trang giá chính thức (link ở mỗi mục).

Quy mô giả định: dùng trong gia đình, không phải sản phẩm thương mại — traffic rất thấp.

## 1. Dịch vụ AWS

| Dịch vụ | Vai trò trong CookBot | Free tier | Mức dùng ước tính của dự án | Giá sau free tier |
|---|---|---|---|---|
| **Lambda** (x86) | Chạy `lambda_bot` (mỗi tin nhắn Telegram) + `lambda_daily` (1 lần/ngày) | 1.000.000 request/tháng + 400.000 GB-giây/tháng — **vĩnh viễn**, không hết hạn sau 12 tháng | ~1.500 request/tháng (≈50 tin/ngày + 1 daily/ngày), ~1.100 GB-giây/tháng (giả định 256MB, ~3s/lần) | $0,20 / 1M request; $0,0000166667 / GB-giây |
| **Lambda Function URL** | Endpoint webhook cho `lambda_bot`, thay API Gateway | Không có phí riêng — tính chung vào Lambda invoke/duration ở trên | — | — |
| **EventBridge Scheduler** (`aws_scheduler_schedule`) | Kích hoạt `lambda_daily` lúc 9h sáng giờ VN | 14.000.000 lần kích hoạt/tháng — **vĩnh viễn** | 1 lần kích hoạt/ngày (~30/tháng) — nằm sâu trong free tier | $1,00 / 1M lần kích hoạt sau free tier |
| **ECR** (private repo) | Lưu image `Dockerfile.lambda` cho cả 2 function | 500 MB-tháng — **chỉ 12 tháng đầu tài khoản AWS**, không vĩnh viễn | ~1 GB (5 image giữ lại theo lifecycle policy × ~200MB/image) | $0,10 / GB-tháng |
| **CloudWatch Logs** | Log của Lambda (thay `docker compose logs`) | 5 GB/tháng (ingest + lưu trữ), tính theo từng region | Traffic thấp → gần như chắc chắn trong free tier | $0,50/GB ingest (Standard); $0,03/GB-tháng lưu trữ |
| **AWS Budgets** | Cảnh báo khi chi tiêu vượt ngưỡng | Budget chỉ gửi cảnh báo (không có automated action) — **miễn phí, không giới hạn số lượng** | 1 budget | $0 (chỉ tính phí nếu bật "action-enabled" tự động chặn/thu hồi quyền — CookBot không dùng loại này) |

Nguồn: [aws.amazon.com/lambda/pricing](https://aws.amazon.com/lambda/pricing/), [aws.amazon.com/ecr/pricing](https://aws.amazon.com/ecr/pricing/), [aws.amazon.com/cloudwatch/pricing](https://aws.amazon.com/cloudwatch/pricing/), [aws.amazon.com/aws-cost-management/aws-budgets/pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/) — đã kiểm tra trực tiếp trang giá ngày 2026-07-20.

**Tổng AWS ước tính: gần $0/tháng**, trừ phần ECR sau năm đầu tiên (~$0,10/tháng, không đáng kể).

## 2. Chi phí Claude API

Model hiện tại: `claude-haiku-4-5` (mặc định trong `config.py`).

**Giá Haiku 4.5:** $1,00 / triệu token input, $5,00 / triệu token output. (Lưu ý: bản Haiku 3.5 cũ — `claude-3-5-haiku-20241022` — đã bị retire 2026-02-19, nếu `.env` nào còn set `MODEL` về giá trị đó sẽ lỗi 404, không phải vấn đề chi phí mà là bug cần sửa ngay.)

**Ước tính token/ngày** (giả định ~10 tin nhắn chat/ngày từ chị Như + 1 lần gọi thực đơn sáng):

| Loại gọi | Input/lần (system prompt + tin nhắn) | Output/lần | Số lần/ngày | Input/ngày | Output/ngày |
|---|---|---|---|---|---|
| Chat tự do (`brain.ask`, `max_tokens=500`) | ~600 token | ~200 token (thực tế thường ngắn hơn mức trần) | 10 | 6.000 | 2.000 |
| Thực đơn 9h (`brain.daily_menu`, `max_tokens=1500`) | ~750 token | ~1.200 token (2 lựa chọn/bữa) | 1 | 750 | 1.200 |
| **Tổng/ngày** | | | | **~6.750** | **~3.200** |

**Chi phí/ngày:** 6.750/1.000.000 × $1 + 3.200/1.000.000 × $5 ≈ $0,0068 + $0,016 = **~$0,023/ngày**

**Chi phí/tháng (30 ngày):** ~$0,023 × 30 ≈ **~$0,68/tháng**

Đây là số ước tính với traffic thấp và giả định thận trọng (max_tokens ít khi dùng hết). Nếu chị Như chat nhiều hơn 10 tin/ngày hoặc câu trả lời dài hơn giả định, con số này tăng nhanh vì **output đắt gấp 5 lần input** — đây là lý do chính khiến `max_tokens` trong `brain.py` phải khớp sát nhu cầu thật (đã ghi trong CLAUDE.md), không nên để cao hơn mức cần.

**Nhận xét quan trọng:** chi phí Claude API (~$0,68/tháng) **lớn hơn nhiều lần** tổng chi phí hạ tầng AWS (~$0/tháng) — Claude mới là chi phí chính của dự án, không phải AWS. Đây là lý do ngưỡng AWS Budget đặt ở $1 vẫn có ý nghĩa: nó không bắt được chi phí Claude (Anthropic không nằm trong AWS Cost Explorer), nhưng bắt được nếu Lambda/ECR/CloudWatch tăng bất thường (ví dụ bug gây gọi Lambda lặp vô hạn).

Nguồn: [platform.claude.com pricing](https://platform.claude.com/docs/en/pricing) — giá lấy từ cache 2026-06-24 trong hệ thống, **nên đối chiếu lại trực tiếp trước khi coi là số chính thức**.

## 3. Ba cơ chế kiểm soát chi phí đang áp dụng

1. **CloudWatch log retention 14 ngày** — log Lambda tự xoá sau 14 ngày thay vì lưu vô thời hạn, tránh phần "lưu trữ" trong free tier bị lấn dần theo thời gian.
2. **ECR lifecycle policy giữ 5 image gần nhất** — mỗi lần build/push image mới, image cũ thứ 6 trở đi tự động bị xoá, tránh ECR phình dung lượng vô hạn qua mỗi lần deploy.
3. **AWS Budget ngưỡng $1** — cảnh báo qua email khi chi tiêu AWS thực tế đạt 80% và khi dự báo (forecasted) đạt 100% ngưỡng. Chỉ cảnh báo, không tự chặn (xem giải thích bên dưới).
