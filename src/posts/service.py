import logging
import httpx
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException
import asyncio
import json
import os
from src.posts.redis_cache import redis_client
from src.posts import redis_cache, models

logging.basicConfig(level=logging.INFO)

# Get API key from environment variable
GOLD_API_KEY = os.getenv("GOLD_API_KEY", "goldapi-3dwn9sm9pcamod-io")


async def fetch_price_api(client: httpx.AsyncClient, url: str, headers: dict, date: str):
    try:
        response = await client.get(f"{url}?date={date}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'price' not in data:
                raise HTTPException(status_code=500, detail="Invalid response format: price not found")
            price = Decimal(str(data['price']))
            return price
        else:
            logging.error(f"API returned status code {response.status_code}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"API returned status code {response.status_code}"
            )
    except httpx.RequestError as e:
        logging.error(f"Network error: {str(e)}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except (KeyError, ValueError) as e:
        logging.error(f"Invalid response format: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response format from API")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_and_update_gold_price(client: httpx.AsyncClient, url: str, headers: dict):
    try:
        date = datetime.today().strftime("%Y-%m-%d")

        # Try to get from cache first
        cached_price = redis_cache.get_price_from_cache(redis_client, f"gold_price_{date}")
        if cached_price:
            logging.info(f"Retrieved price from cache for date {date}")
            return Decimal(str(cached_price))

        # If not in cache, fetch from API
        task1 = asyncio.create_task(fetch_price_api(client, url, headers, date))
        await asyncio.sleep(2)
        task2 = fetch_price_api(client, url, headers, date)

        price_from_api1 = await task1
        price_from_api2 = await task2

        if price_from_api1 != price_from_api2:
            logging.warning("Gold prices from two requests do not match. Using average price.")
            price = (price_from_api1 + price_from_api2) / 2
        else:
            logging.info(f"Gold prices match\nPrice: {price_from_api1}")
            price = price_from_api1

        # Save to cache
        redis_cache.save_price_to_cache(redis_client, f"gold_price_{date}", str(price))
        return price
    except Exception as e:
        logging.error(f"Error in get_and_update_gold_price: {str(e)}")
        raise


def calculate_gold_price(price: Decimal):
    try:
        ounce_to_gram = Decimal('31.1035')
        luong_to_gram = Decimal('37.5')
        price_per_ounce = price * ounce_to_gram
        price_per_luong = price * luong_to_gram
        return price_per_ounce, price_per_luong, price
    except Exception as e:
        logging.error(f"Error calculating gold price: {str(e)}")
        raise HTTPException(status_code=500, detail="Error calculating gold price")


async def fetch_price_api_api(date: str):
    try:
        url = f"https://www.goldapi.io/api/XAU/USD/{date}"
        headers = {
            "x-access-token": GOLD_API_KEY,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'price' not in data:
                    raise HTTPException(status_code=500, detail="Invalid response format: price not found")

                price_per_ounce = Decimal(str(data['price']))
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
                logging.error(f"API error: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Could not get gold price data for date {date}. Please try again later."
                )
    except httpx.RequestError as e:
        logging.error(f"API connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"API connection error: {str(e)}"
        )
    except Exception as e:
        logging.error(f"Unexpected error in fetch_price_api_api: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )