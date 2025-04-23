# Sử dụng Python 3.10 làm base image
FROM python:3.10

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc trong container
WORKDIR /src

# Cài đặt các dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt
COPY requirements/dev.txt requirements/dev.txt

# Cài đặt các dependency và các công cụ cần thiết
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements/prod.txt \
    && pip install sqlmodel sqlalchemy

# Tải wait-for-it.sh và cấp quyền thực thi
RUN curl -sSL https://github.com/vishnubob/wait-for-it/releases/download/v2.5.0/wait-for-it.sh -o /wait-for-it.sh \
    && chmod +x /wait-for-it.sh

# Copy toàn bộ code vào container
COPY . .

# Mở cổng 8000 cho FastAPI
EXPOSE 8000

# Khởi động ứng dụng với Uvicorn
CMD ["uvicorn", "src.posts.main:app", "--host", "localhost", "--port", "8000"]