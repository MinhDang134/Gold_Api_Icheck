# src/service.py

import logging
import httpx
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException
import asyncio
import json
from src.posts.redis_cache import redis_client
from src.posts import redis_cache, models

logging.basicConfig(level=logging.INFO)
async def fetch_price_api(client: httpx.AsyncClient, url: str, headers: dict, date: str):
    try:# nếu đúng
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


async def fetch_price_api_api(date: str):
    api_key = "goldapi-3dwn9sm9pcamod-io"
    url = f"https://www.goldapi.io/api/XAU/USD/{date}"
    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                price_per_ounce = Decimal(str(data.get('price', 0)))
                price_per_gram = price_per_ounce / Decimal('31.1035')
                price_per_luong = price_per_gram * Decimal('37.5')

                new_price = models.GoldPrice(
                    price=price_per_ounce,
                    price_per_ounce=price_per_ounce,
                    price_per_luong=price_per_luong,
                    price_per_gram=price_per_gram,
                    timestamp=datetime.strptime(date, "%Y-%m-%d")
                )
                return new_price
            else:
                logging.error(f"Lỗi khi gọi API: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Không thể lấy dữ liệu giá vàng cho ngày {date}. Vui lòng thử lại sau."
                )
    except httpx.RequestError as e:
        logging.error(f"Lỗi kết nối API: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi kết nối tới API: {str(e)}"
        )

