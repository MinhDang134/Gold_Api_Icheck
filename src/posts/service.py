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
        await asyncio.sleep(2)#19 khi nó chạy nó sẽ nghỉ 10 giây và trong khi đó thì nhưng việc khác cứ tiếp tục thực hiên

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


async def save_to_redis_list(redis_client, key, data):
    try:
        # Kiểm tra dữ liệu trùng lặp
        current_items = redis_client.lrange(key, 0, -1)

        # Kiểm tra trùng lặp
        for item in current_items:
            existing_item = json.loads(item)
            if existing_item['date'] == data['date']:
                logging.info(f"Dữ liệu cho ngày {data['date']} đã tồn tại")
                return False

        # Thêm dữ liệu mới
        redis_client.lpush(key, json.dumps(data))
        logging.info(f"Đã thêm dữ liệu cho ngày {data['date']}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi thêm dữ liệu vào Redis: {str(e)}")
        return False


async def data_mau():
    try:
        # Xóa dữ liệu cũ trong Redis list (nếu có)
        redis_client.delete('Minhdang_list')

        gold_data = [
            {"date": "2025-01-01", "price": 2001.05},
            {"date": "2025-01-02", "price": 2002.30},
            {"date": "2025-01-03", "price": 2003.15},
            {"date": "2025-01-04", "price": 2004.15},
            {"date": "2025-01-05", "price": 2005.15},
            {"date": "2025-01-06", "price": 2006.15},
            {"date": "2025-01-07", "price": 2007.15},
            {"date": "2025-01-08", "price": 2008.15},
            {"date": "2025-01-09", "price": 2009.15},
            {"date": "2025-01-10", "price": 2010.15},
            {"date": "2025-01-11", "price": 2011.15},
            {"date": "2025-01-12", "price": 2012.15},
            {"date": "2025-01-13", "price": 2013.15},
            {"date": "2025-01-14", "price": 2014.15},
            {"date": "2025-01-15", "price": 2015.15},
            {"date": "2025-01-16", "price": 2016.15},
            {"date": "2025-01-17", "price": 2017.15},
            {"date": "2025-01-18", "price": 2018.15},
            {"date": "2025-01-19", "price": 2019.15},
            {"date": "2025-01-20", "price": 2020.15},
        ]

        # Thêm dữ liệu vào Redis
        for data in gold_data:
            await save_to_redis_list(redis_client, 'Minhdang_list', data)

        logging.info("Đã khởi tạo dữ liệu mẫu trong Redis thành công")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi khởi tạo dữ liệu mẫu: {str(e)}")
        return False
