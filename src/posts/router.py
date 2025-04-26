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
        api_key = "goldapi-aqg6bojsm9wkc6kv-io"
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
            logging.info(f"lưu giá vàng database: {price}")
            return {
                "price": str(price),
                "price_per_ounce": str(price_per_ounce),
                "price_per_luong": str(price_per_luong),
                "price_per_gram": str(price_per_gram),
                "timestamp": new_gold_price.timestamp.isoformat()
            }

    except HTTPException as http_exc:
        logging.error(f"HTTP lỗi : {http_exc.detail}")
        raise
    except Exception as e:
        logging.error(f"Bị lỗi sau : {str(e)}")
        raise HTTPException(status_code=500, detail=f"bị lỗi sau : {str(e)}")


@router.get("/get_price_range/")
async def get_price_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        gold_prices_range = crud.get_gold_prices_in_range(db, start_date, end_date)
        rang_cache = redis_cache.rang_save_date_cache(redis_cache.redis_client, 'Minhdang_list', start_date, end_date)

        if gold_prices_range or rang_cache:
            logging.info("Chay vao 3")
            logging.info(f"Noi Dung la{gold_prices_range}")
            logging.info(f"Noi Dung la{rang_cache}")

            return {
                "gold_prices": [
                    {
                        "price": gp.price,
                        "price_per_ounce": gp.price_per_ounce,
                        "price_per_luong": gp.price_per_luong,
                        "price_per_gram": gp.price_per_gram,
                        "timestamp": gp.timestamp
                    } for gp in gold_prices_range
                ]
                # Phần comment out:
                # 'save_search_gold': [
                #     {
                #         "price": rg['price'],
                #         "price_per_ounce": rg['price_per_ounce'],
                #         "price_per_luong": rg['price_per_luong'],
                #         "price_per_gram": rg['price_per_gram'],
                #         "timestamp": rg['timestamp']
                #     } for rg in rang_cache
                # ]
            }
        else:
            raise HTTPException(status_code=404, detail="Không có dữ liệu trong phạm vi ngày đã cho.")

    except ValueError as e:
        raise HTTPException(status_code=400,
                            detail=f"Ngày tháng không hợp lệ. Bạn hãy nhập theo định dạng YYYY-MM-DD.{str(e)} ")
    except Exception as e:
        logging.error(f"Lỗi khi xử lý yêu cầu siu2: {str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi khi xử lý yêu cầu.")

@router.get("/search_data")
async def search_data(date: str, db: Session = Depends(get_db)):
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="không đúng định dang, vui lòng dùng định dạng YYYY-MM-DD")

        # Try to get from cache first
        try:
            cache_items = redis_client.lrange("Minhdang_list", 0, -1)
            for item in cache_items:
                try:
                    item_data = json.loads(item)
                    if item_data.get('date') == date:
                        logging.info("dữ liệu được lấy từ redis")
                        return item_data
                except json.JSONDecodeError:
                    continue
        except Exception as cache_error:
            logging.warning(f"Cache error: {str(cache_error)}")

        # If not in cache, get from database
        database_save = get_data_indatabase(db, date)
        if database_save:
            logging.info(f"dữ liệu được nhận từ database: {database_save}")
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
                logging.info("dữ liệu được lấy từ api và lưu vào database")
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
                raise HTTPException(status_code=404, detail="không thể lấy giá vàng từ api")
        except HTTPException as api_error:
            raise api_error
        except Exception as e:
            logging.error(f"lỗi lấy data : {str(e)}")
            raise HTTPException(status_code=500, detail=f"lỗi lấy data: {str(e)}")

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"lỗi tìm kiếm dữ liệu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"lỗi xử lý yêu cầu :  {str(e)}")

@router.delete("/clear_redis")
async def clear_redis():
    try:
        all_keys = redis_client.keys("*")
        for key in all_keys:
            redis_client.delete(key)
            logging.info(f"Xóa key: {key}")

        return {"message": f"Xóa thành công {len(all_keys)} keys từ Redis"}
    except Exception as e:
        logging.error(f"lỗi xóa redis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"lỗi xóa redis: {str(e)}")

@router.get("/health")
async def health():
    return {"status": "ok"}