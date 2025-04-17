import redis
from typing import TypeVar
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