import os
from datetime import datetime
import json
import redis
from fastapi.openapi.utils import status_code_ranges
from sqlmodel import Session
import logging
from src.posts import models

# Redis configuration with environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5
)

try:
    redis_client.ping()
    logging.info("Redis kết nối thành công")
except redis.ConnectionError as e:
    logging.error(f"Redis kết nối thất bại: {str(e)}")
    raise


def get_price_from_cache(redis_client, key: str):
    try:
        cached_price = redis_client.get(key)
        if cached_price:
            return json.loads(cached_price)
        return None
    except (redis.RedisError, json.JSONDecodeError) as e:
        logging.error(f"Lỗi dữ liệu từ cache: {str(e)}")
        return None
def save_price_to_cache(redis_client, key: str, value: str):
    try:
        result = redis_client.set(key, value)
        if result:
            logging.info(f"thành công lưu vào  {key} của Redis")
            return True
        else:
            logging.error(f"thất bại lưu vào {key} của Redis")
            return False
    except redis.RedisError as e:
        logging.error(f"Redis lỗi: {str(e)}")
        return False
def rang_save_date_cache(redis_client, key: str, start_date: str, end_date: str):
    try:
        if key == "Minhdang_list":
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

            cache_items = redis_client.lrange(key, 0, -1)
            if not cache_items:
                logging.warning(f"không có data trong key '{key}'")
                return []

            result = []
            for item in cache_items:
                try:
                    existing_item = json.loads(item)
                    item_date = datetime.strptime(existing_item['date'], "%Y-%m-%d")
                    if start_date <= item_date <= end_date:
                        result.append(existing_item)
                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Lỗi json: {str(e)}")
                    continue
            return result
    except (redis.RedisError, ValueError) as e:
        logging.error(f"Lỗi khi xử lý dữ liệu siu: {str(e)}")
        return []