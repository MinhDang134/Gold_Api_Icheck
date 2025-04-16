# src/router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import httpx
import json
from src.posts.Dependecies import get_db
from src.posts.schemas import khung_data
from src.posts.service import get_and_update_gold_price, calculate_gold_price
from src.posts import redis_cache, crud
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from src.posts.redis_cache import redis_client

router = APIRouter()

@router.post("/get_price/")
async def get_price(db: Session = Depends(get_db)):
    try:
        cached_price = redis_cache.get_price_from_cache(redis_cache.redis_client, "gold_price")

        api_key = "goldapi-af6o2qsm9f2jcj1-io"
        url = f"https://www.goldapi.io/api/XAU/USD"

        headers = {
            "x-access-token": api_key
        }

        async with httpx.AsyncClient() as client:
            price = await get_and_update_gold_price(client, url, headers, cached_price)

            price_per_ounce, price_per_luong, price_per_gram = calculate_gold_price(price)

            new_gold_price = crud.gold_crud.create(db, {
                "price": price,
                "price_per_ounce": price_per_ounce,
                "price_per_luong": price_per_luong,
                "price_per_gram": price_per_gram
            })

            logging.info(f"Lưu giá vàng vào database: {price}")
            return {"price": price, "timestamp": new_gold_price.timestamp}

    except HTTPException as http_exc:
        logging.error(f"Đã xảy ra lỗi HTTP: {http_exc.detail}")
        raise http_exc

@router.get("/get_price_range/")
async def get_price_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        gold_prices_range = crud.get_gold_prices_in_range(db, start_date, end_date)

        if gold_prices_range:
            return {"gold_prices": [
                {
                    "id": gp.id,
                    "price": gp.price,
                    "price_per_ounce": gp.price_per_ounce,
                    "price_per_luong": gp.price_per_luong,
                    "price_per_gram": gp.price_per_gram,
                    "timestamp": gp.timestamp
                } for gp in gold_prices_range
            ]}

        api_key = "goldapi-af6o2qsm9f2jcj1-io"
        url = "https://www.goldapi.io/api/XAU/USD"

        headers = {
            "x-access-token": api_key
        }

        async with httpx.AsyncClient() as client:
            all_prices = []
            current_date = start_date_obj

            while current_date <= end_date_obj:
                date_str = current_date.strftime("%Y-%m-%d")
                price = await get_and_update_gold_price(client, url, headers, None)

                formatted_price = str(price)
                new_gold_price = crud.gold_crud.create(db, {
                    "price": price,
                    "price_per_ounce": price * Decimal('31.1035'),
                    "price_per_luong": price * Decimal('37.5'),
                    "price_per_gram": price
                })

                all_prices.append({
                    "date": date_str,
                    "price": price,
                    "timestamp": new_gold_price.timestamp
                })

                current_date += timedelta(days=1)

            return {"gold_prices": all_prices}

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Ngày tháng không hợp lệ. Bạn hãy nhập theo định dạng YYYY-MM-DD.")
    except Exception as e:
        logging.error(f"Lỗi khi xử lý yêu cầu: {str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi khi xử lý yêu cầu.")

@router.get("/search_data", response_model=khung_data)
async def save_date(date: str):
    try:
        data_new = redis_client.get(date)
        if data_new:
            duyet_data = json.loads(data_new)
            print("Data đã được trả về")
            return khung_data(date=duyet_data['date'], price=duyet_data['price'])
    except Exception as e:
        logging.info("Không có dữ liệu nào được trả về ")
        raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho ngày {date} lỗi là {str(e)}")

    gold_minhdang = redis_client.lrange("Minhdang_list", 0, -1)

    for timkiem in gold_minhdang:
        gold_price = json.loads(timkiem)
        try:
            if gold_price['date'] == date:

                return khung_data(
                    date=gold_price['date'],
                    price=gold_price['price']
                )
        except Exception as e:
            logging.info("Không tìm thấy cái nào giống trong database hay cache ")
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho ngày {date} và bị lõi này {str(e)}")
