from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import httpx
import json
import os
from src.posts.Dependecies import get_db
from src.posts.crud import get_data_indatabase
from src.posts.service import get_and_update_gold_price, calculate_gold_price, \
    fetch_price_api, fetch_price_api_api
from src.posts import redis_cache, crud
from datetime import datetime, timedelta
import logging
from src.posts.redis_cache import redis_client, get_price_from_cache

router = APIRouter()

@router.post("/get_price/")
async def get_price(db: Session = Depends(get_db)):
    try:
        api_key = os.getenv("GOLD_API_KEY", "goldapi-3dwn9sm9pcamod-io")
        url = "https://www.goldapi.io/api/XAU/USD"
        headers = {
            "x-access-token": api_key,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            logging.info("Fetching gold price...")
            price = await get_and_update_gold_price(client, url, headers)
            price_per_ounce, price_per_luong, price_per_gram = calculate_gold_price(price)

            new_gold_price = crud.gold_crud.create(db, {
                "price": price,
                "price_per_ounce": price_per_ounce,
                "price_per_luong": price_per_luong,
                "price_per_gram": price_per_gram,
                "timestamp": datetime.now()
            })
            logging.info(f"Saved gold price to database: {price}")
            return {
                "price": str(price),
                "price_per_ounce": str(price_per_ounce),
                "price_per_luong": str(price_per_luong),
                "price_per_gram": str(price_per_gram),
                "timestamp": new_gold_price.timestamp.isoformat()
            }

    except HTTPException as http_exc:
        logging.error(f"HTTP error occurred: {http_exc.detail}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/get_price_range/")
async def get_price_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD")

        gold_prices_range = crud.get_gold_prices_in_range(db, start_date, end_date)
        rang_cache = redis_cache.rang_save_date_cache(redis_cache.redis_client, 'Minhdang_list', start_date, end_date)

        if not gold_prices_range and not rang_cache:
            raise HTTPException(status_code=404, detail="No data found for the specified date range")

        result = {
            "gold_prices": [
                {
                    "id": gp.id,
                    "price": str(gp.price),
                    "price_per_ounce": str(gp.price_per_ounce),
                    "price_per_luong": str(gp.price_per_luong),
                    "price_per_gram": str(gp.price_per_gram),
                    "timestamp": gp.timestamp.isoformat()
                } for gp in gold_prices_range
            ]
        }

        if rang_cache:
            result["cached_prices"] = rang_cache

        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error processing price range request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.get("/search_data")
async def search_data(date: str, db: Session = Depends(get_db)):
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD")

        # Try to get from cache first
        try:
            cache_items = redis_client.lrange("Minhdang_list", 0, -1)
            for item in cache_items:
                try:
                    item_data = json.loads(item)
                    if item_data.get('date') == date:
                        logging.info("Data retrieved from cache")
                        return item_data
                except json.JSONDecodeError:
                    continue
        except Exception as cache_error:
            logging.warning(f"Cache error: {str(cache_error)}")

        # If not in cache, get from database
        database_save = get_data_indatabase(db, date)
        if database_save:
            logging.info(f"Data retrieved from database: {database_save}")
            result = {
                'date': date,
                'gold_prices': [{
                    "id": ldl.id,
                    "price": str(ldl.price),
                    "price_per_ounce": str(ldl.price_per_ounce),
                    "price_per_luong": str(ldl.price_per_luong),
                    "price_per_gram": str(ldl.price_per_gram),
                    "timestamp": ldl.timestamp.isoformat() if ldl.timestamp else None
                } for ldl in database_save]
            }
            return result

        # If not in database, fetch from API
        try:
            api_data = await fetch_price_api_api(date)
            if api_data:
                db.add(api_data)
                db.commit()
                db.refresh(api_data)
                database_save = [api_data]
                logging.info("Data retrieved from API and saved to database")
                result = {
                    'date': date,
                    'gold_prices': [{
                        "id": api_data.id,
                        "price": str(api_data.price),
                        "price_per_ounce": str(api_data.price_per_ounce),
                        "price_per_luong": str(api_data.price_per_luong),
                        "price_per_gram": str(api_data.price_per_gram),
                        "timestamp": api_data.timestamp.isoformat()
                    }]
                }
                return result
            else:
                raise HTTPException(status_code=404, detail="Could not get gold price from API")
        except HTTPException as api_error:
            raise api_error
        except Exception as e:
            logging.error(f"Error fetching from API: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error in search_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.delete("/clear_redis")
async def clear_redis():
    try:
        all_keys = redis_client.keys("*")
        for key in all_keys:
            redis_client.delete(key)
            logging.info(f"Deleted key: {key}")

        return {"message": f"Successfully deleted {len(all_keys)} keys from Redis"}
    except Exception as e:
        logging.error(f"Error clearing Redis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing Redis: {str(e)}")