# Thu tu trien khai (xem giai thich day du trong bao cao):
#   1. terraform apply -target=aws_ecr_repository.cookbot
#   2. docker build + push image len ECR voi tag = var.image_tag
#   3. terraform apply (day du, tao IAM/Lambda/Function URL/Scheduler/Budget)

locals {
  common_env = {
    TELEGRAM_TOKEN    = var.telegram_token
    LOG_BOT_TOKEN     = var.log_bot_token
    ANTHROPIC_API_KEY = var.anthropic_api_key
    ALLOWED_CHAT_IDS  = var.allowed_chat_ids
    ADMIN_CHAT_ID     = var.admin_chat_id
    DAILY_CHAT_IDS    = var.daily_chat_ids != "" ? var.daily_chat_ids : var.allowed_chat_ids
    MIRROR_ALL        = var.mirror_all
    CHEF_NAME         = var.chef_name
    MODEL             = var.model
    LAT               = var.lat
    LON               = var.lon
  }

  image_uri = "${aws_ecr_repository.cookbot.repository_url}:${var.image_tag}"

  # aws_cloudwatch_log_group.arn tra ve tu API da co san hau to ":*" —
  # strip roi tu them lai de tranh double-wildcard lam sai IAM resource match.
  log_group_arn_bot   = "${replace(aws_cloudwatch_log_group.bot.arn, ":*", "")}:*"
  log_group_arn_daily = "${replace(aws_cloudwatch_log_group.daily.arn, ":*", "")}:*"
}

# ---------------------------------------------------------------------------
# ECR
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "cookbot" {
  name = "cookbot"
}

resource "aws_ecr_lifecycle_policy" "cookbot" {
  repository = aws_ecr_repository.cookbot.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Giu toi da 5 image gan nhat"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------------------
# CloudWatch Log Groups — tao truoc va dat ten dung "/aws/lambda/<function>"
# de Lambda ghi vao day thay vi tu tao group khac khong co retention.
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "bot" {
  name              = "/aws/lambda/cookbot-bot-prd"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "daily" {
  name              = "/aws/lambda/cookbot-daily-prd"
  retention_in_days = 14
}

# ---------------------------------------------------------------------------
# IAM cho Lambda — chi cap logs:CreateLogStream + PutLogEvents, scope dung
# 2 log group da tao o tren. Khong dung AWSLambdaBasicExecutionRole (managed
# policy do cap them logs:CreateLogGroup tren toan bo /aws/lambda/*).
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "cookbot-lambda-exec-prd"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_logs" {
  statement {
    effect  = "Allow"
    actions = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [
      local.log_group_arn_bot,
      local.log_group_arn_daily,
    ]
  }
}

resource "aws_iam_policy" "lambda_logs" {
  name   = "cookbot-lambda-logs-prd"
  policy = data.aws_iam_policy_document.lambda_logs.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_logs.arn
}

# ---------------------------------------------------------------------------
# Lambda functions — cung 1 image ECR, khac image_config.command
# (xem DECISIONS.md muc "mot image cho nhieu handler")
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "bot" {
  function_name = "cookbot-bot-prd"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  timeout       = 60
  memory_size   = 256

  image_config {
    command = ["runners.lambda_bot.lambda_handler"]
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.bot.name
  }

  environment {
    variables = merge(local.common_env, {
      WEBHOOK_SECRET = var.webhook_secret
    })
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_logs]
}

resource "aws_lambda_function" "daily" {
  function_name = "cookbot-daily-prd"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  timeout       = 60
  memory_size   = 256

  image_config {
    command = ["runners.lambda_daily.lambda_handler"]
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.daily.name
  }

  environment {
    variables = local.common_env
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_logs]
}

# ---------------------------------------------------------------------------
# Function URL cho cookbot-bot-prd — Telegram khong ky SigV4 nen phai NONE,
# xac thuc that nam trong core/handler.py (WEBHOOK_SECRET) chu khong o day.
# authorization_type = NONE khong tu dong cho phep goi cong khai — can them
# aws_lambda_permission rieng, thieu no Telegram se nhan 403.
# ---------------------------------------------------------------------------

resource "aws_lambda_function_url" "bot" {
  function_name      = aws_lambda_function.bot.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "function_url_public" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.bot.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "function_url_invoke" {
  statement_id  = "FunctionURLAllowInvokeAction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "*"
}

# ---------------------------------------------------------------------------
# EventBridge Scheduler — goi cookbot-daily-prd luc 9h sang gio VN.
# Scheduler tu dung role_arn de InvokeFunction, khong can aws_lambda_permission
# rieng nhu EventBridge Rule kieu cu.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler_invoke_daily" {
  name               = "cookbot-scheduler-invoke-prd"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "scheduler_invoke_daily" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.daily.arn]
  }
}

resource "aws_iam_policy" "scheduler_invoke_daily" {
  name   = "cookbot-scheduler-invoke-daily-prd"
  policy = data.aws_iam_policy_document.scheduler_invoke_daily.json
}

resource "aws_iam_role_policy_attachment" "scheduler_invoke_daily" {
  role       = aws_iam_role.scheduler_invoke_daily.name
  policy_arn = aws_iam_policy.scheduler_invoke_daily.arn
}

resource "aws_scheduler_schedule" "daily" {
  name                         = "cookbot-daily-9am-prd"
  schedule_expression          = "cron(0 9 * * ? *)"
  schedule_expression_timezone = "Asia/Ho_Chi_Minh"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.daily.arn
    role_arn = aws_iam_role.scheduler_invoke_daily.arn
  }
}

# ---------------------------------------------------------------------------
# AWS Budget — chi canh bao (khong action-enabled), xem giai thich trong
# bao cao ve vi sao AWS khong tu chan chi tieu.
# ---------------------------------------------------------------------------

resource "aws_budgets_budget" "cookbot" {
  name         = "cookbot-monthly-prd"
  budget_type  = "COST"
  limit_amount = "1"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
