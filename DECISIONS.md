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
