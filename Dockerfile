FROM python:3.12-slim

# Giờ Việt Nam thay vì UTC
ENV TZ=Asia/Bangkok
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Copy requirements TRƯỚC để tận dụng layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code sau
COPY core/ core/
COPY runners/ runners/
COPY *.py .

CMD ["python", "bot.py"]