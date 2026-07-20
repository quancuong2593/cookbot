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
│   ├── handler.py        # handle_message(chat_id, text) -> str | None — gate whitelist + gọi brain
│   └── daily.py          # main() — build thực đơn 9h, gửi cho DAILY_CHAT_IDS
├── runners/               # Biết mình chạy ở đâu — lo transport (Telegram) + trình bày (mirror log)
│   ├── local.py           # Process 1: long polling (python-telegram-bot), gọi core.handler
│   └── scheduler.py       # Process 2: vòng lặp ngủ đến 9h rồi gọi core.daily.main()
├── bot.py, daily.py, scheduler.py   # DEPRECATED — shim mỏng gọi sang runners/core, sẽ xoá sau khi ổn định
├── .env                  # Secrets — KHÔNG BAO GIỜ commit
├── Dockerfile
└── docker-compose.yml
```

**Ranh giới `core/` vs `runners/`:**
- `core/` — logic thuần, nhận/trả kiểu dữ liệu cơ bản (`str`, `None`), không phụ thuộc kênh nhắn tin hay runtime. Đây là phần sẽ chạy giống hệt trên Lambda và trên VPS. Gate whitelist (`config.ALLOWED`) và cảnh báo "⛔ Người lạ nhắn" nằm ở đây — đó là quyết định bảo mật gắn liền với nghiệp vụ, không phải chuyện hiển thị.
- `runners/` — biết mình đang chạy ở đâu (long-polling trên VPS, hay sau này event-driven trên Lambda) và trên kênh nào (Telegram). Lo việc dịch dữ liệu từ/tới kênh và mọi thứ thuộc về trình bày — mirror log (`👀 ... hỏi / 🤖 Bot đáp`, phụ thuộc `MIRROR_ALL`) nằm ở đây, không phải trong `core/`.

**Hai loại process, khác vòng đời:**
- `runners/local.py` — reactive, chạy liên tục, chờ tin nhắn đến
- `core/daily.py` — proactive, chạy 30 giây rồi kết thúc, gọi bởi `runners/scheduler.py`

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

`bot.py` / `daily.py` / `scheduler.py` ở gốc vẫn chạy được (shim deprecated, gọi sang `runners.*`/`core.*`), nhưng lệnh và code mới dùng đường dẫn `-m runners.*` / `-m core.*` ở trên.

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

## Quy ước khi làm việc với Claude Code

- Giải thích bằng tiếng Việt, giữ nguyên thuật ngữ kỹ thuật tiếng Anh
- Tôi đang học — khi sửa code, giải thích *vì sao* chứ không chỉ đưa code
- Ưu tiên giải pháp đơn giản, dễ hiểu hơn là giải pháp "thông minh"
- Trước khi refactor, xác nhận hành vi không đổi
- Không tự ý thêm dependency mới nếu chưa cần thiết

## Trạng thái hiện tại & việc tiếp theo

**Đã xong:** bot trả lời realtime, gate whitelist, mirror log qua bot riêng, thực đơn 9h sáng (2 option/bữa, cuối tuần thêm bữa trưa), Docker Compose 2 service, tách `core/` (logic thuần) khỏi `runners/` (transport + trình bày) để chuẩn bị chạy song song Lambda/VPS.

**Đang làm:** tách môi trường dev/prd, dựng quy trình Git chuẩn, viết test, CI/CD.

**Kế hoạch xa:** conversation memory (bot đang stateless, quên câu trước), family profile (dị ứng, món ghét), feedback loop bằng inline buttons, deploy AWS Lambda (thêm `runners/lambda.py` gọi lại `core.handler`), port sang Messenger.

**Nợ kỹ thuật đã biết:**
- Thêm người dùng phải sửa `.env` + restart container
- Chưa có test tự động
- Chưa chống gửi trùng nếu scheduler restart đúng lúc 9h
- Log ghi trong container, mất khi `docker compose down`
- `bot.py` / `daily.py` / `scheduler.py` ở gốc là shim deprecated — xoá ở commit riêng sau khi `runners.*`/`core.*` chạy ổn định qua Docker
