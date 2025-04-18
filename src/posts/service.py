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
async def fetch_price_api(client: httpx.AsyncClient, url: str, headers: dict, date: str):

    try:
        response = await client.get(f"{url}?date={date}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            price = Decimal(data['price'])
            return price
        else:
            logging.info(f"Giá trị trả về API trạng thái là {response.status_code}")
            raise HTTPException(status_code=500, detail="Không thể lấy dữ liệu từ API")
    except Exception as e:
        logging.info(f"Lỗi khi gọi API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi không gọi được API: {str(e)}")
async def get_and_update_gold_price(client: httpx.AsyncClient, url: str, headers: dict, cached_price):
    date = datetime.today().strftime("%Y-%m-%d")
    if cached_price:
        price = Decimal(cached_price)
        task1 = asyncio.create_task(fetch_price_api(client, url, headers, date))
        await asyncio.sleep(2)
        task2 = fetch_price_api(client, url, headers, date)

        price_from_api1 = await task1
        price_from_api2 = await task2

        if price_from_api1 != price_from_api2:
            logging.info("Giá vàng từ hai request không trùng nhau. Cập nhật giá mới.")
            logging.info(f"Giá vàng request 1 là :{price_from_api1}")
            logging.info(f"Giá vàng request 2 là :{price_from_api2}")
            formatted_price = str(price_from_api2)
            redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price)
            price = price_from_api2
        else:
            logging.info(f"Giá vàng từ hai request trùng nhau\ngiá vàng 1 {price_from_api1}\ngiá vàng 2 là {price_from_api2}")
    else:
        price = await fetch_price_api(client, url, headers)
        formatted_price = str(price)
        if redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price):
            logging.info(f"Đã lưu thông tin: {formatted_price} vào Redis")
        else:
            logging.error("Lỗi khi lưu giá vào Redis.")
    return price
def calculate_gold_price(price: Decimal):

    ounce_to_gram = Decimal('31.1035')
    luong_to_gram = Decimal('37.5')
    price_per_ounce = price * ounce_to_gram
    price_per_luong = price * luong_to_gram
    return price_per_ounce, price_per_luong, price


async def save_to_redis_list(redis_client, key, data):
    try:
        current_items = redis_client.lrange(key, 0, -1)
        for item in current_items:
            existing_item = json.loads(item)
            if existing_item['date'] == data['date']:
                logging.info(f"Dữ liệu cho ngày {data['date']} đã tồn tại")
                return False
        redis_client.lpush(key, json.dumps(data))
        logging.info(f"Đã thêm dữ liệu cho ngày {data['date']}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi thêm dữ liệu vào Redis: {str(e)}")
        return False


async def data_mau():
    try:


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
        for data in gold_data:
            await save_to_redis_list(redis_client, 'Minhdang_list', data)

        logging.info("Đã khởi tạo dữ liệu mẫu trong Redis thành công")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi khởi tạo dữ liệu mẫu: {str(e)}")
        return False
