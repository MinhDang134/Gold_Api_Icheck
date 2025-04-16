import redis


redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

try:
    redis_client.ping()
    print("Kết nối cứ gọi là thành công")
except redis.ConnectionError:
    print("Không kết nối thành công ")

# Kiểm tra xem dữ liệu có trong cache không
def get_price_from_cache(redis_client,key:str):
    cached_price = redis_client.get(key)
    if cached_price:
        return cached_price
    return None

def save_price_to_cache(redis_client, key: str, value: str):
    result = redis_client.set(key, value)
    if result:
        print(f"Đã lưu {key} vào Redis.")
    else:
        print(f"Lỗi khi lưu {key} vào Redis.")