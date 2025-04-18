from datetime import datetime
import json
import redis
from fastapi.openapi.utils import status_code_ranges
from sqlmodel import Session
import logging
from src.posts import models
import json
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
try:
    redis_client.ping()
    print("Kết nối cứ gọi là thành công")
except redis.ConnectionError:
    print("Không kết nối thành công ")

def get_price_from_cache(redis_client,key:str):
    cached_price = redis_client.get(key)
    if cached_price:
        return cached_price
    return None
def laydulieuder_save(key:str):
    cache_save = redis_client.get(key)
    if cache_save:
     return json.loads(cache_save)
    return None


def save_price_to_cache(redis_client, key: str, value: str):
    result = redis_client.set(key, value)
    if result:
        print(f"Đã lưu {key} vào Redis.")
    else:
        print(f"Lỗi khi lưu {key} vào Redis.")


def rang_save_date_cache(redis_client, key: str, start_date: str, end_date: str):
    try:
        if key == "Minhdang_list":
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            cache_items = redis_client.lrange(key, 0, -1)
            if not cache_items:
                logging.error(f"Không có dữ liệu trong Redis với key '{key}'")
                return []
            result = []
            for item in cache_items:
                try:

                    existing_item = json.loads(item)
                    item_date = datetime.strptime(existing_item['date'], "%Y-%m-%d")

                    if start_date <= item_date <= end_date:
                        result.append(existing_item)
                except json.JSONDecodeError as e:
                    logging.error(f"Lỗi khi phân tích cú pháp JSON: {e}")
                    continue


            if not result:
                logging.error(f"Không tìm thấy dữ liệu trong phạm vi ngày từ {start_date} đến {end_date}")
                return []

            return result
    except Exception as e:
        logging.error(f"Lỗi khi xử lý dữ liệu: {str(e)}")
        return []
