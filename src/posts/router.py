# src/router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import httpx
from src.posts.Dependecies import get_db
from src.posts.service import get_and_update_gold_price, calculate_gold_price
from src.posts import redis_cache, crud
from datetime import datetime, timedelta
from decimal import Decimal
import logging

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
