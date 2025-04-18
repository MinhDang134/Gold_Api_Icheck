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

# Kiểm tra xem dữ liệu có trong cache không

def get_price_from_cache(redis_client,key:str):
    #2 sau khi nhận được cái key với cả redis client của thằng kia thì nó sẽ bát đầu kiển tra
    # kiểm tra xem cái key thằng kia nó chuyền vào thông tin gì bên trong cache redis không
    cached_price = redis_client.get(key)
    if cached_price:# nếu có
        return cached_price
    return None# nếu không thì ra null thôi
def laydulieuder_save(key:str):
    cache_save = redis_client.get(key)
    if cache_save:
     return json.loads(cache_save)
    return None

#27 sau khi nhận được những đối số bên kia truyền vào gồm nhưng redis_client, key,value
def save_price_to_cache(redis_client, key: str, value: str):
    #28 thì nó sẽ set cái key đó cho dữ liệu trong redis và thế là không ổn sau phải cải thiện cái này mình dùng sai mục đích cache
    result = redis_client.set(key, value)
    if result:
        print(f"Đã lưu {key} vào Redis.")
    else:
        print(f"Lỗi khi lưu {key} vào Redis.")


def rang_save_date_cache(redis_client, key: str, start_date: str, end_date: str):
    try:
        if key == "Minhdang_list":
            # Chuyển đổi start_date và end_date thành datetime
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

            # Lấy tất cả các phần tử trong Redis list
            cache_items = redis_client.lrange(key, 0, -1)

            # Nếu không có dữ liệu trong Redis
            if not cache_items:
                logging.error(f"Không có dữ liệu trong Redis với key '{key}'")
                return []

            result = []
            for item in cache_items:
                try:
                    # Chuyển từ chuỗi JSON thành dict
                    existing_item = json.loads(item)
                    # Chuyển đổi 'date' từ chuỗi thành datetime
                    item_date = datetime.strptime(existing_item['date'], "%Y-%m-%d")

                    # Kiểm tra nếu ngày trong phạm vi start_date và end_date
                    if start_date <= item_date <= end_date:
                        result.append(existing_item)
                except json.JSONDecodeError as e:
                    logging.error(f"Lỗi khi phân tích cú pháp JSON: {e}")
                    continue

            # Nếu không tìm thấy dữ liệu phù hợp
            if not result:
                logging.error(f"Không tìm thấy dữ liệu trong phạm vi ngày từ {start_date} đến {end_date}")
                return []

            return result
    except Exception as e:
        logging.error(f"Lỗi khi xử lý dữ liệu: {str(e)}")
        return []
