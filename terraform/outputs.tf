output "function_url" {
  description = "URL webhook của cookbot-bot-prd — đăng ký với Telegram qua setWebhook (kèm secret_token = webhook_secret)"
  value       = aws_lambda_function_url.bot.function_url
}

output "ecr_repository_url" {
  description = "URL repository ECR — dùng để docker build/push image trước khi apply hoặc khi cập nhật image_tag"
  value       = aws_ecr_repository.cookbot.repository_url
}
