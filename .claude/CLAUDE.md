# CookBot — Trợ lý nấu ăn gia đình

## Bối cảnh dự án

Bot Telegram gợi ý món ăn healthy theo nguyên lý Đông y, dựa trên thời tiết Hà Nội.

**Người dùng thật (khách hàng):** vợ tôi — bếp trưởng của gia đình, tên gọi trong bot là "chị Như". Không rành kỹ thuật. Mọi thứ đến tay chị phải chỉn chu: không tin nhắn rác, không lỗi hiển thị, không im lặng bất thường.

**Người vận hành:** tôi (dev + ops). Đang học DevOps (Docker, Git, CI/CD, Linux, AWS) và học chứng chỉ Claude Certified Architect – Foundations. Dự án này là sân tập cho cả hai.

**Nguyên tắc chi phí:** ưu tiên giải pháp miễn phí hoặc gần như miễn phí. Dùng Claude Haiku, Open-Meteo (free, không cần key), hạ tầng chạy local rồi sẽ lên AWS Lambda free tier.

## Kiến trúc hiện tại

```
cookbot/
├── config.py            # Đọc toàn bộ env vào một chỗ
├── notifier.py          # Gửi tin cho user + gửi log cho admin (2 bot khác nhau)
├── brain.py             # Gọi Claude API, chứa system prompts
├── weather.py           # Lấy thời tiết Open-Meteo
├── core/                 # Logic nghiệp vụ thuần — không import telegram, không biết mình chạy ở đâu
│   ├── handler.py        # handle_message(chat_id, text) -> str | None — gate whitelist + gọi brain, có ngữ cảnh bữa/thời tiết
│   ├── daily.py          # main(slot) — build thực đơn 9h sáng hoặc bữa sáng cuối tuần 21h, gửi cho DAILY_CHAT_IDS
│   └── mealtime.py       # current_meals(day_index, hour) — xác định đang hỏi cho bữa nào, thuần túy để test độc lập
├── runners/               # Biết mình chạy ở đâu — lo transport (Telegram) + trình bày (mirror log)
│   ├── local.py           # Process 1 (VPS): long polling (python-telegram-bot), gọi core.handler
│   ├── scheduler.py       # Process 2 (VPS): vòng lặp ngủ đến 9h rồi gọi core.daily.main()
│   ├── lambda_bot.py      # Handler Lambda: webhook Telegram qua Function URL, gọi core.handler
│   └── lambda_daily.py    # Handler Lambda: gọi core.daily.main(), kích hoạt bởi EventBridge cron
├── tests/                 # pytest cho core/ + notifier.py, mock hoàn toàn Claude/Telegram/Open-Meteo
│   ├── conftest.py        # reload_config fixture + env giả mặc định
│   ├── test_handler.py
│   ├── test_daily.py
│   ├── test_config.py
│   ├── test_lambda_bot.py
│   └── test_notifier.py   # setup_logging() không tạo FileHandler khi chạy trên Lambda
├── terraform/             # Hạ tầng production trên AWS — xem terraform/*.tf, chi tiết ở mục riêng bên dưới
├── .env                  # Secrets — KHÔNG BAO GIỜ commit
├── Dockerfile             # Image cho runners/local.py + runners/scheduler.py (VPS), CMD mặc định `python -m runners.local`
├── Dockerfile.lambda      # Image chung cho lambda_bot + lambda_daily (CMD override lúc deploy)
└── docker-compose.yml
```

**Ranh giới `core/` vs `runners/`:**
- `core/` — logic thuần, nhận/trả kiểu dữ liệu cơ bản (`str`, `None`), không phụ thuộc kênh nhắn tin hay runtime. Đây là phần sẽ chạy giống hệt trên Lambda và trên VPS. Gate whitelist (`config.ALLOWED`) và cảnh báo "⛔ Người lạ nhắn" nằm ở đây — đó là quyết định bảo mật gắn liền với nghiệp vụ, không phải chuyện hiển thị.
- `runners/` — biết mình đang chạy ở đâu (long-polling trên VPS, hay sau này event-driven trên Lambda) và trên kênh nào (Telegram). Lo việc dịch dữ liệu từ/tới kênh và mọi thứ thuộc về trình bày — mirror log (`👀 ... hỏi / 🤖 Bot đáp`, phụ thuộc `MIRROR_ALL`) nằm ở đây, không phải trong `core/`.

**Hai loại process, khác vòng đời:**
- `runners/local.py` — reactive, chạy liên tục, chờ tin nhắn đến
- `core/daily.py` — proactive, chạy 30 giây rồi kết thúc, gọi bởi `runners/scheduler.py` (VPS/dev) hoặc `runners/lambda_daily.py` qua EventBridge Scheduler (production)

**Giới hạn đã biết của `runners/scheduler.py` (VPS/dev):** vòng lặp ngủ chỉ tính "9h sáng hôm sau", **không** biết tới 2 lịch bữa sáng cuối tuần (21h thứ Sáu/Bảy) mà production có qua `aws_scheduler_schedule` trong `terraform/main.tf`. Đây là quyết định có chủ đích, không phải thiếu sót — VPS là môi trường dev, không cần khớp 100% lịch production. Muốn test slot `"evening"` trên VPS thì gọi tay: `docker compose run --rm bot python -c "import asyncio, core.daily as d; asyncio.run(d.main('evening'))"`.

## Quy tắc thiết kế (bắt buộc tuân thủ)

**Gate trước khi tốn tiền.** Kiểm tra whitelist (`config.ALLOWED`) PHẢI nằm trước lệnh gọi Claude API. Người lạ nhắn thì bot im lặng hoàn toàn và ghi cảnh báo vào log.

**Observability không được làm sập hệ thống chính.** Mọi lệnh gửi log bọc trong try/except. Bot log hỏng thì bot chính vẫn phải phục vụ bình thường.

**Secrets tiêm lúc chạy, không nướng vào image.** `.env` nằm trong `.gitignore` và `.dockerignore`. Docker nhận secrets qua `--env-file` / `env_file`.

**Tách config khỏi code.** Mọi giá trị có thể thay đổi (tên bếp trưởng, toạ độ, model, giờ gửi, feature flag) đọc từ env qua `config.py`. Không hardcode.

**Adapter pattern cho kênh nhắn tin.** Logic gọi Claude không được biết mình đang chạy trên Telegram hay Messenger. Có kế hoạch port sang Messenger sau, nên phần gửi/nhận tin phải tách riêng.

**`core/` tuyệt đối không import thư viện `telegram`.** Đây là ranh giới cứng, không chỉ quy ước: logic trong `core/` nhận vào kiểu dữ liệu thuần (`chat_id: str`, `text: str`), không nhận `Update`/`Context` hay bất kỳ object nào của một kênh cụ thể. Chỉ `runners/` được phép import thư viện transport và quyết định cách trình bày kết quả (kể cả mirror log).

**Timezone tường minh.** Luôn dùng `ZoneInfo("Asia/Bangkok")`, không dùng giờ hệ thống. Container mặc định chạy UTC.

## Prompt engineering — những gì đã học được

- Xưng hô: phải cấm cụ thể ("không dùng 'bạn', 'cô', 'chú'"), không chỉ khuyên chung chung
- Lời khen: định lượng tần suất ("khoảng 1 trong 3 tin"), nếu không model khen mọi câu
- Hai lựa chọn món: phải ràng buộc "khác nhóm đạm chính, khác cách chế biến", nếu không model trả về hai biến thể của cùng một món
- `max_tokens` phải khớp độ dài output mong đợi, thiếu thì tin nhắn bị cắt cụt

## Lệnh thường dùng

```bash
# Chạy trần (dev nhanh)
python -m runners.local
python -m core.daily               # test tin 9h sáng ngay, không cần chờ

# Docker
docker compose up -d --build
docker compose ps
docker compose logs -f bot
docker compose logs -f scheduler
docker compose run --rm bot python -m core.daily    # chạy daily thủ công
docker compose down
```

```bash
# --- Production (AWS Lambda, hạ tầng quản lý bằng Terraform trong terraform/) ---

# Build & push image — LUÔN kèm 2 cờ nay, thiếu là Lambda báo "image manifest not supported"
# (xem mục "Cạm bẫy đã gặp" #1)
docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
  -f Dockerfile.lambda -t <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/cookbot:<tag> \
  --push .

# Terraform — luôn truyền image_tag khớp tag vừa push (KHÔNG dùng "latest" cho production,
# xem DECISIONS.md mục "Tag image bằng git SHA")
cd terraform
terraform plan  -var="image_tag=<tag>"
terraform apply -var="image_tag=<tag>"

# Xem log gần nhất của cả 2 function (CloudWatch, không phải docker compose logs)
aws logs tail /aws/lambda/cookbot-bot-prd   --since 1h --follow
aws logs tail /aws/lambda/cookbot-daily-prd --since 1h --follow

# Test thực đơn 9h thủ công, không cần chờ EventBridge Scheduler
aws lambda invoke --function-name cookbot-daily-prd --payload '{}' /tmp/out.json && cat /tmp/out.json

# Chẩn đoán Function URL — 3 lệnh, mỗi lệnh xác nhận đúng 1 nấc của webhook
FUNCTION_URL=$(cd terraform && terraform output -raw function_url)

# 1) Không header xác thực — mong đợi 403
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"message":{"chat":{"id":111},"text":"hi"}}'

# 2) Header có nhưng sai giá trị — mong đợi 403
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: sai-secret" \
  -d '{"message":{"chat":{"id":111},"text":"hi"}}'

# 3) Header đúng — mong đợi 200 (nếu vẫn lỗi ở bước này dù #1, #2 đúng, xem
# "Cạm bẫy đã gặp" #3 — thường là thiếu permission lambda:InvokeFunction)
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $WEBHOOK_SECRET" \
  -d '{"message":{"chat":{"id":111},"text":"hi"}}'
```

## Biến môi trường

| Biến | Ý nghĩa |
|---|---|
| `ANTHROPIC_API_KEY` | Key Claude API |
| `TELEGRAM_TOKEN` | Token bot chính (nói chuyện với user) |
| `LOG_BOT_TOKEN` | Token bot log (gửi bản sao cho admin) |
| `ALLOWED_CHAT_IDS` | Whitelist chat_id, phân cách bằng dấu phẩy |
| `ADMIN_CHAT_ID` | chat_id của tôi, nơi nhận log |
| `DAILY_CHAT_IDS` | Ai nhận tin 9h sáng |
| `MIRROR_ALL` | `1` = mirror cả tin của admin (dùng khi test) |
| `CHEF_NAME` | Tên gọi bếp trưởng, mặc định "chị Như" |
| `MODEL` | Model Claude, mặc định `claude-haiku-4-5` |
| `LAT` / `LON` | Toạ độ lấy thời tiết |
| `WEBHOOK_SECRET` | Bí mật xác thực webhook Telegram gọi vào `runners/lambda_bot.py` (header `X-Telegram-Bot-Api-Secret-Token`), chỉ dùng khi chạy trên Lambda |
| `MEAL_BOUNDARY_HOUR` | Giờ ranh giới (0-23, mặc định `12`) để xác định T7/CN đang hỏi "trưa+tối" hay chỉ "tối" — xem `core/mealtime.py` |

## Quy ước khi làm việc với Claude Code

- Giải thích bằng tiếng Việt, giữ nguyên thuật ngữ kỹ thuật tiếng Anh
- Tôi đang học — khi sửa code, giải thích *vì sao* chứ không chỉ đưa code
- Ưu tiên giải pháp đơn giản, dễ hiểu hơn là giải pháp "thông minh"
- Trước khi refactor, xác nhận hành vi không đổi
- Không tự ý thêm dependency mới nếu chưa cần thiết

## Terraform — hạ tầng production (đã triển khai)

`terraform/` đã được viết và `apply` thật lên AWS — production hiện chạy trên Lambda, không còn là kế hoạch. Danh sách tài nguyên (xem [COSTS.md](../COSTS.md) cho chi phí ước tính từng mục):

- `aws_ecr_repository` — chứa image build từ `Dockerfile.lambda`
- `aws_ecr_lifecycle_policy` — giữ tối đa 5 image gần nhất (khớp COSTS.md)
- `aws_lambda_function` × 2 — `cookbot-bot-prd` (CMD `runners.lambda_bot.lambda_handler`) và `cookbot-daily-prd` (CMD `runners.lambda_daily.lambda_handler`), cùng trỏ vào 1 image ECR, khác `image_config.command` (xem DECISIONS.md mục "một image cho nhiều handler"); timeout 60s, memory 256MB, không đặt `reserved_concurrent_executions` (xem "Cạm bẫy đã gặp" #4)
- `aws_lambda_function_url` — gắn vào `cookbot-bot-prd`, `authorization_type = NONE`, dùng làm webhook URL đăng ký với Telegram (`setWebhook` + `secret_token` = `WEBHOOK_SECRET`) — xem DECISIONS.md mục "Function URL authorization_type = NONE"
- `aws_scheduler_schedule` × 3 (EventBridge Scheduler, không phải Rule kiểu cũ), `schedule_expression_timezone = "Asia/Ho_Chi_Minh"`, đều kích hoạt `cookbot-daily-prd`: 9h sáng hàng ngày (`input = {slot="morning"}`), 21h thứ Sáu và 21h thứ Bảy (`input = {slot="evening"}`, chuẩn bị bữa sáng cuối tuần) — thay cho vòng lặp ngủ của `runners/scheduler.py`
- `aws_cloudwatch_log_group` × 2 — 1 cho mỗi Lambda, `retention_in_days = 14`
- `aws_budgets_budget` — ngưỡng $1, cảnh báo ở 80% actual và 100% forecasted, gửi email — xem chi tiết giải thích ngay dưới đây
- Biến môi trường của cả 2 Lambda đọc từ `aws_lambda_function.environment` (Terraform variable/secret, không nướng vào image — đúng nguyên tắc "Secrets tiêm lúc chạy" ở trên)

### `aws_budgets_budget` — chi tiết

- `budget_type = "COST"`, `limit_amount = "1"`, `limit_unit = "USD"`, `time_unit = "MONTHLY"`
- 2 `notification` block:
  - `threshold = 80`, `threshold_type = "PERCENTAGE"`, `notification_type = "ACTUAL"` — đã tiêu thật 80% ngưỡng
  - `threshold = 100`, `threshold_type = "PERCENTAGE"`, `notification_type = "FORECASTED"` — AWS dự báo cả tháng sẽ vượt 100% ngưỡng, dù hiện tại chưa tiêu tới
  - Cả 2 gửi tới email của tôi qua `subscriber_email_address`
- Đây là budget **chỉ cảnh báo** (không action-enabled) — theo COSTS.md, loại này miễn phí, không tính vào quota "2 budget miễn phí/tháng" của loại action-enabled

**Vì sao AWS chỉ cảnh báo mà không tự chặn chi tiêu:** AWS Budgets mặc định chỉ là hệ thống giám sát (monitoring), không phải cầu dao ngắt mạch. Lý do kỹ thuật: chi phí AWS thường phát sinh từ tài nguyên đã và đang chạy (Lambda đang xử lý request, dữ liệu đã lưu trên ECR/CloudWatch) — AWS không thể "hoàn tác" chi phí đã phát sinh, và việc tự động xoá/tắt tài nguyên sản xuất có thể gây hại nhiều hơn (mất dữ liệu, sập dịch vụ đang chạy) so với việc để một khoản phí nhỏ phát sinh rồi con người quyết định. Muốn AWS **tự chặn** thật sự phải cấu hình riêng "action-enabled budget" (tự áp IAM policy chặn quyền, hoặc gọi Lambda tự tắt tài nguyên) — loại này mất phí ($0,10/ngày sau 2 budget đầu) và có rủi ro tự làm gián đoạn dịch vụ, nên CookBot ở quy mô gia đình không cần tới.

**Budget nên đặt ở đâu trong cấu trúc Terraform:** `aws_budgets_budget` không thuộc về tài nguyên nào cụ thể (không phải Lambda, không phải ECR) — nó là chính sách ở cấp **billing/account**, không đổi theo môi trường (dev/prod) như các resource khác. Nên đặt trong một module/file riêng (ví dụ `budget.tf` hoặc module `governance/`), tách khỏi module `lambda/` hay `ecr/` — để có thể `terraform apply` chỉ phần hạ tầng ứng dụng mà không đụng tới chính sách chi tiêu, và ngược lại sửa ngưỡng budget không cần plan lại toàn bộ Lambda/ECR.

## Cạm bẫy đã gặp

Bốn lỗi thật đã gặp khi đưa CookBot lên Lambda — mỗi cái đều "build/apply thành công" nhưng fail ở bước sau, không báo lỗi ngay tại chỗ gây ra, nên dễ tốn thời gian debug sai chỗ.

**1. Docker Buildx tự sinh attestation → Lambda báo "image manifest not supported"**
`docker buildx build` (mặc định trên Docker Desktop/Engine bản mới) tự động đính kèm provenance + SBOM attestation vào manifest, biến kết quả build thành một *OCI image index* (manifest list nhiều kiến trúc/attestation) thay vì 1 image manifest đơn giản. AWS Lambda **không hỗ trợ** định dạng index này — báo lỗi `"image manifest not supported"` khi tạo/update function, dù bước `docker build` lúc trước không báo lỗi gì. Khắc phục: build với `docker buildx build --provenance=false --sbom=false --platform linux/amd64 ...` để ra đúng 1 image manifest chuẩn OCI mà Lambda hiểu được (xem lệnh đầy đủ ở mục "Lệnh thường dùng"). **Chưa đưa vào CI/CD** — nhớ giữ 2 cờ này khi dựng pipeline, thiếu là mọi lần deploy từ CI fail y hệt.

**2. Lambda filesystem read-only → `FileHandler` làm crash logging**
`notifier.setup_logging()` từng luôn tạo `FileHandler("cookbot.log")`, gây `OSError: [Errno 30] Read-only file system: '/var/task/cookbot.log'` ngay khi `core/daily.py` gọi tới trên Lambda (`/var/task` là nơi code giải nén từ image, không ghi được; `/tmp` ghi được nhưng không persistent nên cũng vô nghĩa để log). Đã sửa: chỉ thêm `FileHandler` khi **không** có biến `AWS_LAMBDA_FUNCTION_NAME` trong môi trường; luôn có `StreamHandler` vì Lambda tự gom stdout/stderr vào CloudWatch; thêm `force=True` cho `logging.basicConfig()` vì Lambda runtime đã tự cấu hình sẵn 1 handler gốc trước khi code chạy — thiếu `force=True` thì lệnh `basicConfig()` bị bỏ qua lặng lẽ.

**3. Function URL cần HAI permission, thiếu 1 cái → `AccessDeniedException`, log Lambda trống trơn**
`authorization_type = NONE` trên Function URL không tự cấp quyền gọi công khai — cần **2 permission tách biệt**: `lambda:InvokeFunctionUrl` (cho phép gọi qua route Function URL) VÀ `lambda:InvokeFunction` (permission "gốc" mọi cách gọi Lambda đều cần, không riêng gì Function URL). `main.tf` ban đầu chỉ khai báo permission thứ nhất — thiếu permission thứ hai nên request bị chặn **trước khi vào tới code Lambda**, vì vậy log CloudWatch trống trơn (không có gì để log vì handler chưa từng chạy), dễ khiến người debug đi tìm sai chỗ (tưởng code lỗi, thực ra request chưa bao giờ chạm code). Khắc phục: thêm `aws_lambda_permission` thứ hai với `action = "lambda:InvokeFunction"`. Ghi chú: AWS Console tự tạo cả 2 permission này khi bật Function URL qua giao diện web — đây là lý do "làm qua Console chạy ngay, làm qua Terraform lại lỗi", một khác biệt kinh điển giữa 2 cách thao tác.

**4. `reserved_concurrent_executions` không đặt được vì quota account chỉ có 10**
AWS bắt buộc giữ tối thiểu 10 "unreserved concurrent executions" cho toàn account/region (để các Lambda khác luôn có ít nhất 10 slot chạy chung). Account mới mặc định tổng quota concurrency cũng chỉ đúng 10 — nên đặt `reserved_concurrent_executions` cho bất kỳ function nào (dù chỉ 1) cũng làm phần unreserved còn lại tụt dưới 10 → AWS từ chối request. Hiện tại: **không đặt** `reserved_concurrent_executions` cho cả 2 Lambda, dùng chung pool unreserved của account/region — chấp nhận được ở quy mô traffic gia đình hiện tại. Muốn đặt reserved sau này (ví dụ đảm bảo `cookbot-bot-prd` không bị Lambda khác giành hết slot) phải xin AWS tăng quota tổng trước.

## Trạng thái hiện tại & việc tiếp theo

**Đã xong:** bot trả lời realtime, gate whitelist, mirror log qua bot riêng, thực đơn 9h sáng (2 option/bữa, cuối tuần thêm bữa trưa) + bữa sáng cuối tuần gửi tối hôm trước (21h T6/T7, dùng dự báo ngày mai), giải thích ảnh hưởng thời tiết lên cơ thể theo Đông y trước phần gợi ý món, chat tự do biết đang hỏi cho bữa nào (`core/mealtime.py`), Docker Compose 2 service (VPS/dev), tách `core/` (logic thuần) khỏi `runners/` (transport + trình bày), bộ test pytest cho `core/` + `notifier.py`. **Production đã chạy thật trên AWS Lambda** — hạ tầng quản lý hoàn toàn bằng Terraform (`terraform/`), cả `cookbot-bot-prd` (webhook Telegram qua Function URL) và `cookbot-daily-prd` (thực đơn 9h + 2 lịch 21h qua EventBridge Scheduler) đều hoạt động, đã đi qua và vá xong 4 cạm bẫy thật (xem mục "Cạm bẫy đã gặp").

**Đang làm:** tách môi trường dev/prd rõ ràng hơn (hiện dev = VPS/Docker Compose, prd = Lambda — chưa có staging), dựng quy trình Git chuẩn, dựng CI/CD (build image đúng cờ, tag theo git SHA, tự động `terraform apply`).

**Kế hoạch xa:** conversation memory (bot đang stateless, quên câu trước), family profile (dị ứng, món ghét), feedback loop bằng inline buttons, port sang Messenger.

**Nợ kỹ thuật đã biết:**
- Thêm người dùng phải sửa `.env` + restart container
- Chưa chống gửi trùng nếu scheduler restart đúng lúc 9h — **chỉ áp dụng cho VPS/dev** (vòng lặp ngủ của `runners/scheduler.py`). Production dùng `aws_scheduler_schedule` (EventBridge Scheduler), không có vòng lặp tự tính giờ nên không có kiểu race này (rủi ro duy nhất còn lại là "Webhook retry" ở bullet dưới, khác cơ chế).
- Log ghi trong container, mất khi `docker compose down` — **chỉ áp dụng cho VPS/dev** (`runners/local.py`/`runners/scheduler.py` qua `docker-compose.yml`). Production trên Lambda không có vấn đề này — log đi CloudWatch, `retention_in_days = 14` (xem mục Terraform).
- **Webhook retry có thể gây trả lời trùng:** `runners/lambda_bot.py` gọi Claude (`handle_message`) xong mới trả `200` cho Telegram. Nếu Claude chậm hơn thời gian Telegram sẵn sàng chờ, Telegram coi webhook lỗi và gửi lại đúng update đó → Claude bị gọi 2 lần cho cùng 1 câu hỏi, chị Như nhận 2 câu trả lời. Hướng xử lý khi cần: (a) trả `200` ngay sau khi xác thực + parse xong, đẩy việc gọi Claude vào SQS xử lý bất đồng bộ, hoặc (b) đơn giản hơn — lưu `update_id` đã xử lý (ví dụ DynamoDB/S3 nhỏ) làm idempotency key, thấy trùng thì trả `200` luôn mà không gọi lại Claude. Chưa làm vì rủi ro thấp trong thực tế (Haiku thường trả lời dưới 2 giây) và muốn giữ kiến trúc đơn giản cho tới khi có traffic thật.
- **Tag image `"latest"` khiến `terraform apply` báo "No changes" dù image đã đổi** — Terraform chỉ so chuỗi `image_uri`, không hỏi ECR image thật là gì (xem DECISIONS.md mục "Tag image bằng git SHA"). Phải chuyển sang tag theo git SHA khi dựng CI/CD, `"latest"` hiện chỉ dùng cho deploy thủ công.
- **Permission `lambda:InvokeFunction` trên Function URL đang rộng hơn bản Console tự tạo** — `aws_lambda_permission.function_url_invoke` (action `lambda:InvokeFunction`) thiếu điều kiện `lambda:InvokedViaFunctionUrl` mà Console tự thêm để giới hạn quyền đó CHỈ cho phép invoke đến từ chính Function URL. Đã thử gán `function_url_auth_type` cho resource này nhưng AWS từ chối thẳng: `"FunctionUrlAuthType is only supported for lambda:InvokeFunctionUrl action"` — tham số đó chỉ hợp lệ trên permission có action `InvokeFunctionUrl` (permission đầu), không áp dụng được cho `InvokeFunction` (permission thứ hai). `aws_lambda_permission` của Terraform provider hiện không có tham số nào để khai báo điều kiện `lambda:InvokedViaFunctionUrl`, nên permission trong `main.tf` là quyền `InvokeFunction` không điều kiện — rộng hơn cần thiết (bất kỳ principal nào gọi được `InvokeFunction`, không riêng gì qua Function URL). Rủi ro thấp (function vẫn chỉ chạy được với `WEBHOOK_SECRET` đúng, gate nằm ở tầng ứng dụng), nhưng là chỗ lệch giữa "làm đúng qua Console" và "làm qua Terraform" cần nhớ. Đã `apply` thành công với 2 permission này, không có drift.
- **Chưa có healthcheck cho `cookbot-daily-prd`** — nếu EventBridge Scheduler không kích hoạt đúng 9h (hoặc kích hoạt nhưng Lambda lỗi âm thầm), không có cơ chế nào báo — chỉ phát hiện khi chị Như thắc mắc sao chưa thấy thực đơn. Hướng xử lý khi cần: CloudWatch Alarm trên metric `Invocations`/`Errors` của `cookbot-daily-prd`, hoặc đơn giản hơn — dead man's switch kiểu healthchecks.io ping sau mỗi lần `daily.main()` chạy xong.
- **Dùng `terraform apply -target=aws_ecr_repository.cookbot` để phá vòng lặp ECR↔Lambda lúc bootstrap là workaround, không phải quy trình chuẩn** — `-target` bỏ qua toàn bộ dependency graph, dễ để state lệch khỏi config nếu dùng quen tay cho việc khác ngoài lần đầu deploy. Chỉ nên dùng đúng 1 lần lúc tạo ECR repo trước khi có image; các lần `apply` sau phải chạy đầy đủ, không `-target`.
