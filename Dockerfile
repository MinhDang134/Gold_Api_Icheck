FROM python:3.13

# Ngăn ghi file .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /src

# Copy yêu cầu cài đặt trước để tận dụng layer cache
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt
COPY requirements/dev.txt requirements/dev.txt

# Cài các gói cần thiết
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements/prod.txt \
    && pip install sqlmodel sqlalchemy

# Tải script wait-for-it
RUN curl -sSL https://github.com/vishnubob/wait-for-it/releases/download/v2.5.0/wait-for-it.sh -o /wait-for-it.sh \
    && chmod +x /wait-for-it.sh

# Copy toàn bộ mã nguồn
COPY . .

# Mở cổng chạy app
EXPOSE 8000

# Lệnh khởi động
CMD ["uvicorn", "src.posts.main:app", "--host", "0.0.0.0", "--port", "8000"]
