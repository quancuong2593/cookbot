variable "aws_region" {
  description = "AWS region triển khai"
  type        = string
  default     = "ap-southeast-1"
}

variable "image_tag" {
  description = "Tag của image trong ECR mà 2 Lambda sẽ chạy. Image PHẢI đã tồn tại trong ECR với tag này trước khi apply — xem thứ tự triển khai."
  type        = string
  default     = "latest"
}

# --- Secrets: không có giá trị mặc định, bắt buộc truyền qua terraform.tfvars ---

variable "telegram_token" {
  description = "Token bot Telegram chính (nói chuyện với user)"
  type        = string
  sensitive   = true
}

variable "log_bot_token" {
  description = "Token bot Telegram dùng để gửi log cho admin"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "API key Claude"
  type        = string
  sensitive   = true
}

variable "webhook_secret" {
  description = "Bí mật xác thực webhook Telegram (header X-Telegram-Bot-Api-Secret-Token), chỉ dùng bởi cookbot-bot-prd"
  type        = string
  sensitive   = true
}

# --- Cấu hình nghiệp vụ, không phải secret nhưng vẫn không hardcode ---

variable "allowed_chat_ids" {
  description = "Whitelist chat_id, phân cách bằng dấu phẩy"
  type        = string
}

variable "admin_chat_id" {
  description = "chat_id nhận log từ bot log"
  type        = string
}

variable "daily_chat_ids" {
  description = "Ai nhận tin 9h sáng, phân cách bằng dấu phẩy. Để trống = dùng chung allowed_chat_ids (khớp mặc định trong config.py)"
  type        = string
  default     = ""
}

variable "mirror_all" {
  description = "\"1\" = mirror cả tin nhắn của admin (dùng khi test)"
  type        = string
  default     = "0"
}

variable "chef_name" {
  description = "Tên gọi bếp trưởng"
  type        = string
  default     = "chị Như"
}

variable "model" {
  description = "Model Claude"
  type        = string
  default     = "claude-haiku-4-5"
}

variable "lat" {
  description = "Vĩ độ lấy thời tiết (Hà Nội)"
  type        = string
  default     = "21.03"
}

variable "lon" {
  description = "Kinh độ lấy thời tiết (Hà Nội)"
  type        = string
  default     = "105.85"
}

variable "budget_alert_email" {
  description = "Email nhận cảnh báo AWS Budget"
  type        = string
}
