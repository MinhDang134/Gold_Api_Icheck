# src/service.py

import logging
import httpx
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException
import asyncio
import json
from src.posts.redis_cache import redis_client
from src.posts import redis_cache

logging.basicConfig(level=logging.INFO)
#12 hàm phía dưới vừa gọi đến hàm này, thì nó sẽ cho nhưng cái tham số tương ứng với đối số bên kia chuyền vào
async def fetch_price_api(client: httpx.AsyncClient, url: str, headers: dict, date: str):

    try: #13 trường hợp nếu đúng, thì client nó cũng cấp phương thức ghét nó sẽ lấy ra link, ngày và hearder của đict
        response = await client.get(f"{url}?date={date}", headers=headers)
        #14 nếu mà trang thái bằng 200 nghĩa là trang thái trả về có dữ liệu và đúng thì...
        if response.status_code == 200:
            data = response.json() #15 lấy data json về từ reponse trả về từ api
            price = Decimal(data['price']) #16 lấy được cái giá của json đó thì lại ép kiểu thành decimal
            return price # 17 trả về price
        else: #18 nếu lỗi thì trả về lỗi như bên này thôi
            logging.info(f"Giá trị trả về API trạng thái là {response.status_code}")
            raise HTTPException(status_code=500, detail="Không thể lấy dữ liệu từ API")
    except Exception as e:
        logging.info(f"Lỗi khi gọi API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi không gọi được API: {str(e)}")
#6 hàm này sẽ nhận nhưng đối số mà bên đó chuyền vào
async def get_and_update_gold_price(client: httpx.AsyncClient, url: str, headers: dict, cached_price):
   #7 khai báo date và lưu định dạng ngày hôm này
    date = datetime.today().strftime("%Y-%m-%d")
   #8 cái trường hợp mà cached_price có dự liệu trong redis
    if cached_price:#9 nếu đúng
        price = Decimal(cached_price) #10 nó sẽ gán cho cái giá từ redis đó ép thành kiểu Decimal
        #11 cách này để tạo một request làm việc song song với những thuọc tính truyền vào fetch_price_api
        task1 = asyncio.create_task(fetch_price_api(client, url, headers, date))  # Request thứ 1
        await asyncio.sleep(10)#19 khi nó chạy nó sẽ nghỉ 10 giây và trong khi đó thì nhưng việc khác cứ tiếp tục thực hiên

        task2 = fetch_price_api(client, url, headers, date)#20 đến request thứ 2

        price_from_api1 = await task1#21 chờ cả hai cái nó thực hiện
        price_from_api2 = await task2#22 chờ hai cái cùng hthucwj hiện

        if price_from_api1 != price_from_api2:#23 nếu mà giá trị request 1 mà khác request 2
            logging.info("Giá vàng từ hai request không trùng nhau. Cập nhật giá mới.")#24 in ra các giá trị
            logging.info(f"Giá vàng request 1 là :{price_from_api1}")#24 in ra các giá trị
            logging.info(f"Giá vàng request 2 là :{price_from_api2}")#24 in ra các giá trị
            formatted_price = str(price_from_api2) #25 lưu cái giá vàng sau vào formatted
            #26 gọi đến hàm save_price_to_cache trong redis để lưu vào redis với tham số là redis_client,key, value
            redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price)
            #29 sau đó thì gán cái giá trị thứ 2 vào price
            price = price_from_api2
        else:
            logging.info(f"Giá vàng từ hai request trùng nhau\ngiá vàng 1 {price_from_api1}\ngiá vàng 2 là {price_from_api2}")
    else:#30 trường hợp còn lại là nó sẽ lấy dữ liệu từ fetch sau đó nó thành string để mà truyền vào redis
        price = await fetch_price_api(client, url, headers)
        formatted_price = str(price)
        #31 gửi thông tin các thứ lưu như bình thường thôi có vẻ phần này không cần thiết lắm
        if redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price):
            logging.info(f"Đã lưu thông tin: {formatted_price} vào Redis")
        else:
            logging.error("Lỗi khi lưu giá vào Redis.")
    #32 return ra giá vàng
    return price

#34 sau khi nhận được giá vàng nó sẽ tính toán
def calculate_gold_price(price: Decimal):
    ounce_to_gram = Decimal('31.1035')
    luong_to_gram = Decimal('37.5')
    price_per_ounce = price * ounce_to_gram
    price_per_luong = price * luong_to_gram
#35 nó sẽ return ra 3 cái này
    return price_per_ounce, price_per_luong, price


def save_to_redis_list(redis_client, key, data):
    try:
        # Bước 1: Lấy tất cả các phần tử hiện có trong Redis list
        current_items = redis_client.lrange(key, 0, -1)  # Get all items from the list

        # Bước 2: Kiểm tra xem phần tử mới đã có trong list chưa
        # Chúng ta sẽ so sánh ngày của phần tử mới với các phần tử hiện có trong danh sách
        is_duplicate = False
        for item in current_items:
            # Chuyển đổi item từ dạng chuỗi JSON thành dict và kiểm tra 'date'
            existing_item = json.loads(item)  # Chuyển string thành dict
            if existing_item['date'] == data['date']:  # Kiểm tra xem ngày có trùng không
                is_duplicate = True  # Nếu trùng, đánh dấu là trùng
                break  # Dừng vòng lặp khi tìm thấy phần tử trùng

        # Bước 3: Nếu không trùng lặp, thêm phần tử mới vào Redis list
        if not is_duplicate:
            # Chuyển data thành chuỗi JSON và thêm vào Redis list
            redis_client.lpush(key, json.dumps(data))
            logging.info(f"Đã lưu vào Redis List với key '{key}': {data}")
        else:
            return f"Thêm thành công"

    except Exception as e:

        logging.error(f"Lỗi khi lưu vào Redis List: {str(e)}")


async def data_mau():
    gold_data = [ # tạo ra một bảng dữ liệu sẵn
        {"date": "2025-01-01", "price": 2054.05},
        {"date": "2025-01-02", "price": 2060.30},
        {"date": "2025-01-03", "price": 2070.15},
        {"date": "2025-01-04", "price": 2033.15},
        {"date": "2025-01-05", "price": 2072.15},
        {"date": "2025-01-06", "price": 2073.15},
        {"date": "2025-01-07", "price": 2074.15},
        {"date": "2025-01-08", "price": 2075.15},
        {"date": "2025-01-09", "price": 2075.15},
        {"date": "2025-01-10", "price": 2075.15},
        {"date": "2025-01-11", "price": 2075.15},
        {"date": "2025-01-12", "price": 2075.15},
        {"date": "2025-01-13", "price": 2075.15},

    ]
    for data_push in gold_data: # duyệt từng phần tử rồi push lên redis
        save_to_redis_list(redis_client, 'Minhdang_list', data_push)
