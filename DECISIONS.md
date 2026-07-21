# Quyết định kiến trúc

## [2026-07-20] Tách core/ khỏi runners/

**Bối cảnh:** CookBot trước đây gộp logic nghiệp vụ (gate whitelist, gọi Claude, build thực đơn) và logic transport (long polling Telegram, gửi tin, mirror log) chung trong `bot.py`, `daily.py`, `scheduler.py`. Có kế hoạch chạy song song trên hai môi trường khác nhau — VPS (dev, long polling 24/7) và AWS Lambda (production, event-driven) — nên cần logic nghiệp vụ chạy được giống hệt nhau ở cả hai nơi mà không kéo theo phụ thuộc vào cách nào đang polling hay ai đang gọi nó.

**Quyết định:** Tách thành hai thư mục theo ranh giới rõ ràng:
- `core/` — logic thuần, hàm `handle_message(chat_id: str, text: str) -> str | None` và `daily.main()`, tuyệt đối không import thư viện `telegram`, không nhận vào object đặc thù của một kênh (`Update`, `Context`...). Gate whitelist và cảnh báo "⛔ Người lạ nhắn" thuộc về `core/` vì đó là quyết định bảo mật gắn với nghiệp vụ.
- `runners/` — biết mình chạy ở đâu (`local.py` polling liên tục, `scheduler.py` ngủ đến 9h) và trên kênh nào (Telegram). Chịu trách nhiệm dịch dữ liệu từ/tới kênh và mọi thứ thuộc về trình bày — mirror log (`👀`/`🤖`, phụ thuộc `MIRROR_ALL`) chuyển hẳn từ core sang đây.

`bot.py`, `daily.py`, `scheduler.py` cũ giữ lại làm shim mỏng gọi sang vị trí mới, đánh dấu `# DEPRECATED`, để không phá lệnh chạy quen thuộc trong lúc chuyển tiếp; sẽ xoá ở commit riêng sau khi `runners.*`/`core.*` chạy ổn định qua Docker.

**Lý do:** Khi thêm `runners/lambda.py` sau này, nó chỉ cần gọi lại đúng `core.handler.handle_message` / `core.daily.main` — không phải sửa hay copy logic nghiệp vụ. Đồng thời `core/` trở nên dễ test hơn vì không cần mock thư viện Telegram, chỉ cần gọi hàm với `str` đầu vào.

**Đánh đổi:** Thêm một lớp gián tiếp (runner → core) cho một codebase còn nhỏ — với quy mô hiện tại, tách sớm này chưa có lợi ích tức thời, chỉ trả giá trước cho việc port sang Lambda/Messenger sắp tới. Runner giờ phải tự lấy `user_name` từ `Update` và tự quyết định gửi mirror log, nghĩa là logic mirror log sẽ phải viết lại (không tái dùng được) khi thêm runner cho kênh khác — chấp nhận vì đó vốn là phần đặc thù kênh, không nên dùng chung.

## [2026-07-20] Inject notify_admin vào handle_message thay vì import notifier

**Bối cảnh:** Khi viết pytest cho `core/handler.py`, test nhánh "chat_id bị chặn" bắt buộc phải mock `notifier.send_log` — vì `handle_message` gọi thẳng module đó để gửi cảnh báo "⛔ Người lạ nhắn". Việc phải mock lộ ra rằng `core/` tuy không import `telegram` trực tiếp, nhưng vẫn import cứng `notifier` — một module import `telegram` và làm I/O thật (HTTP request tới Telegram API). Core vì vậy chưa thực sự độc lập: muốn test hay muốn chạy `core/handler.py` một mình đều phải kéo theo `notifier`.

**Quyết định:** Bỏ `import notifier` khỏi `core/handler.py`. `handle_message` nhận thêm tham số bắt buộc `notify_admin: Callable[[str], Awaitable[None]]` — một callback do caller truyền vào, không có giá trị mặc định. `runners/local.py` truyền `notifier.send_log` vào lúc gọi (`handle_message(cid, text, notify_admin=notifier.send_log)`). Gate whitelist và cảnh báo "⛔ Người lạ nhắn" vẫn nằm trong core như quyết định trước — chỉ đổi *cách* core gọi ra ngoài, không đổi *nơi* logic đó sống. Thêm test kiến trúc đọc source `core/handler.py` và khẳng định chuỗi `"notifier"` không xuất hiện, để ai vô tình thêm lại import sẽ bị test chặn ngay.

**Lý do:** `core/` giờ chỉ còn phụ thuộc `config` và `brain` — hai module thuần, không I/O tại thời điểm import. Test có thể truyền thẳng `AsyncMock()` cho `notify_admin` mà không cần biết `notifier` tồn tại, và `core/handler.py` có thể chạy độc lập (kể cả trên Lambda) mà không kéo theo `python-telegram-bot`.

**Đánh đổi:** Chữ ký `handle_message` dài hơn và có một tham số bắt buộc — mọi nơi gọi hàm này (hiện tại chỉ `runners/local.py`, sau này cả `runners/lambda.py`) phải nhớ truyền `notify_admin`, quên truyền là lỗi ngay lúc gọi (`TypeError`, không có default để lỡ rơi vào). Đổi lại lỗi này lộ ra sớm và ồn ào thay vì im lặng gửi nhầm log, nên chấp nhận được.

## [2026-07-20] Một Docker image cho cả 2 Lambda handler

**Bối cảnh:** Thêm 2 entry point chạy trên AWS Lambda — `runners/lambda_bot.py` (webhook Telegram qua Function URL) và `runners/lambda_daily.py` (thực đơn 9h, kích hoạt bởi EventBridge cron). Cả hai dùng chung 100% dependency (`requirements.txt`) và chung code nền (`config.py`, `notifier.py`, `brain.py`, `weather.py`, `core/`) — khác biệt duy nhất là entry point nào được gọi.

**Quyết định:** Build một `Dockerfile.lambda` duy nhất chứa cả 2 handler, `CMD` mặc định trỏ `runners.lambda_bot.lambda_handler`. Khi tạo Lambda function bằng Terraform, function `cookbot-daily` sẽ override `image_config.command` thành `runners.lambda_daily.lambda_handler`, dùng chung một image URI trên ECR với function `cookbot-bot`.

**Lý do:** AWS Lambda container image cho phép override `CMD` lúc tạo/update function mà không cần build lại image — nên 1 image vật lý phục vụ được nhiều function logic khác nhau. Lợi ích: 1 pipeline build/push thay vì 2 (đúng nguyên tắc chi phí thấp, đơn giản đã ghi trong CLAUDE.md), không lệch phiên bản dependency giữa 2 function vì cả hai luôn chạy từ đúng 1 layer filesystem, chỉ cần theo dõi 1 image tag khi rollback thay vì đồng bộ 2 tag.

**Đánh đổi:** Image của mỗi function "mang theo" cả code của handler kia dù không dùng tới (không đáng kể — vài KB Python so với phần nặng nhất là các thư viện dùng chung). Quan trọng hơn: 2 function luôn bị khoá cùng một phiên bản image — không thể rollback hoặc cập nhật riêng lẻ một function mà không ảnh hưởng đến function còn lại. Chấp nhận được vì cả hai luôn được deploy cùng lúc từ cùng một codebase, việc luôn đồng bộ là hành vi mong muốn chứ không phải hạn chế.

Ngoài phần trên, quyết định dùng container image cho Lambda (thay vì zip package) còn kéo theo một số ràng buộc từ chính mô hình chạy của Lambda, không riêng gì việc dùng chung 1 image:

- **Lambda chạy container theo mô hình ephemeral** — container chỉ khởi động khi có request tới, "đóng băng" (freeze) giữa các lần gọi nếu còn warm, và bị xoá hẳn nếu im lặng đủ lâu (thường vài chục phút không có invocation). Đây khác hẳn `docker compose up -d` trên VPS, nơi container sống liên tục 24/7.
- **Hệ quả trực tiếp:** filesystem của container **không persistent** — bất cứ gì ghi ra đĩa (ví dụ `cookbot.log` mà `notifier.setup_logging()` tạo ra) sẽ mất khi container bị xoá, nên `runners/lambda_bot.py` và `runners/lambda_daily.py` cố tình không gọi `notifier.setup_logging()` (đã ghi chú trong code) mà để log đi thẳng CloudWatch. Tương tự, bất kỳ state nào cần sống qua nhiều lần gọi (ví dụ idempotency key theo `update_id` — xem mục nợ kỹ thuật "Webhook retry" trong CLAUDE.md) phải nằm ở dịch vụ ngoài container, ví dụ DynamoDB, chứ không thể lưu biến trong RAM hay file cục bộ và kỳ vọng lần gọi sau còn thấy.
- **`CMD` trong `Dockerfile.lambda` không phải lệnh shell để chạy** như `CMD ["python", "bot.py"]` ở `Dockerfile` (VPS) — Lambda Runtime Interface Client diễn giải `CMD` như đường dẫn tới **handler function** (`module.submodule.function_name`), không `exec` nó như một tiến trình độc lập. Vì vậy Terraform override được `CMD` qua `image_config.command` mà không cần build lại image: nó chỉ đổi handler nào được Runtime Interface Client gọi khi có event tới, không phải đổi "lệnh chạy" theo nghĩa Docker thông thường.

## [2026-07-21] Tag image bằng git SHA thay vì "latest" khi có CI/CD

**Bối cảnh:** `terraform/variables.tf` có `var.image_tag` (mặc định `"latest"`), dùng để build `image_uri = "<ecr-repo>:<image_tag>"` cho cả 2 Lambda. Nếu quy trình deploy luôn build/push vào tag `"latest"` rồi `terraform apply`, `apply` sẽ báo **"No changes"** dù bytes thật trong ECR đã đổi.

**Cơ chế gây ra:** `terraform plan`/`apply` không hỏi AWS "image trong ECR bây giờ là gì" — nó chỉ so sánh **chuỗi** `image_uri` trong config với chuỗi đã lưu ở lần apply trước trong `terraform.tfstate`. Chuỗi `"<repo>:latest"` không đổi giữa 2 lần deploy (dù nội dung image phía sau tag đó đã đổi), nên Terraform không thấy diff và không gọi API cập nhật function — nó không có cơ chế nào để biết "latest" hôm nay trỏ tới digest khác hôm qua. Về phía AWS: Lambda container image resolve tag → digest **tại thời điểm gọi update**, rồi giữ nguyên digest đó cho tới lần update kế tiếp; không có update nào được gọi thì function tiếp tục chạy digest cũ, image mới nằm im trong ECR mà không ai dùng tới.

**Quyết định:** Khi dựng CI/CD (việc tiếp theo trong CLAUDE.md), mỗi lần build sẽ tag image bằng git SHA của commit đang deploy (`docker build -t <ecr-repo>:<git-sha> .`), và truyền giá trị đó vào Terraform qua biến có sẵn: `terraform apply -var="image_tag=<git-sha>"` (hoặc `TF_VAR_image_tag`). Không dùng `"latest"` cho pipeline production — giá trị mặc định `"latest"` trong `variables.tf` chỉ còn ý nghĩa cho lần deploy thủ công đầu tiên/thử nghiệm.

**Lý do:** Mỗi commit tạo một chuỗi tag khác nhau → `image_uri` trong config **thực sự đổi** giữa 2 lần apply → Terraform thấy diff thật, gọi API cập nhật function → Lambda resolve đúng digest mới. Đây chính là lý do `image_tag` đã được thiết kế thành **biến** thay vì hardcode `"latest"` thẳng trong `main.tf` ngay từ đầu — chỉ còn thiếu kỷ luật ở phía pipeline gọi Terraform với giá trị đúng. Tag theo git SHA còn cho một lợi ích phụ: biết chính xác `image_tag` nào đang chạy production là biết chính xác commit nào — dò lỗi hay rollback không cần đoán.

**Đánh đổi:** Mỗi lần deploy tạo một image mới trong ECR (không ghi đè `"latest"` nữa) — dung lượng tăng nhanh hơn, nhưng `aws_ecr_lifecycle_policy` đã có sẵn (giữ 5 image gần nhất) nên tự dọn, không cần thêm gì. Rollback không còn là "sửa 1 dòng rồi apply" đơn giản như trước — phải biết chính xác git SHA của bản muốn quay lại (tra qua `git log` hoặc tag Git release đi kèm mỗi lần deploy) rồi truyền lại đúng `image_tag` đó, tức là cần lưu vết SHA nào tương ứng lần deploy nào — việc CI/CD phải làm khi dựng (ví dụ ghi vào changelog hoặc GitHub Release), chưa có ở bước này.

## [2026-07-21] Nợ kỹ thuật có ý thức: IAM User chạy Terraform đang là AdministratorAccess

**Bối cảnh:** Để chạy `terraform apply` từ máy dev, cần một identity AWS CLI có quyền tạo được mọi resource trong `terraform/` (ECR, IAM role/policy, Lambda, Function URL, EventBridge Scheduler, CloudWatch Log Group, Budget). Đây là vấn đề "con gà quả trứng" lúc bootstrap: chưa có Terraform nào chạy được để tự tạo ra một IAM policy least-privilege đúng đủ quyền cho chính nó.

**Quyết định:** Tạm thời dùng IAM User có gắn managed policy `AdministratorAccess` để chạy Terraform, thay vì thiết kế một custom policy least-privilege ngay từ đầu.

**Lý do:** Ưu tiên có hạ tầng chạy được trước (dự án đang ở giai đoạn học/dựng nền, một mình tôi vận hành, chưa có traffic thật), tránh việc vừa học Terraform vừa phải tự liệt kê chính xác từng action IAM cần thiết (rất dễ thiếu quyền, gây debug vòng vo giữa "lỗi do Terraform" và "lỗi do thiếu quyền IAM" — mất thời gian hơn giá trị nhận được ở quy mô hiện tại).

**Đánh đổi — đây là nợ kỹ thuật có ý thức, không phải sơ suất:** `AdministratorAccess` mâu thuẫn trực tiếp với chính nguyên tắc least-privilege đang áp dụng bên trong `main.tf` (IAM role của Lambda chỉ được cấp đúng `logs:CreateLogStream`/`PutLogEvents` trên 2 log group cụ thể, IAM role của Scheduler chỉ được `lambda:InvokeFunction` trên đúng 1 function) — người vận hành (tôi) lại có quyền rộng hơn tất cả các resource đó cộng lại. Rủi ro cụ thể: access key của IAM User này bị lộ (commit nhầm, máy dev bị xâm nhập) đồng nghĩa toàn bộ tài khoản AWS bị chiếm, không chỉ riêng CookBot. Hướng xử lý sau này: thay `AdministratorAccess` bằng một custom IAM policy chỉ liệt kê đúng các action/resource mà `terraform/` cần (ecr:*, iam:CreateRole/PutRolePolicy giới hạn theo path/prefix `cookbot-*`, lambda:*, scheduler:*, logs:*, budgets:*, tất cả scope theo tên resource `cookbot-*`), hoặc tốt hơn — bỏ hẳn access key dài hạn, chuyển sang AWS SSO / assume-role tạm thời (`aws sts assume-role`, credentials hết hạn sau vài giờ) cho việc chạy Terraform.
