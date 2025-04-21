from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import httpx
import json
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
        cached_price = redis_cache.get_price_from_cache(redis_client, "gold_price")
        api_key = "goldapi-3dwn9sm9pcamod-io"
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
        gold_prices_range = crud.get_gold_prices_in_range(db, start_date, end_date)
        rang_cache = redis_cache.rang_save_date_cache(redis_cache.redis_client, 'Minhdang_list', start_date, end_date)

        if gold_prices_range or rang_cache:
            return {
                "gold_prices": [
                    {
                        "id": gp.id,
                        "price": gp.price,
                        "price_per_ounce": gp.price_per_ounce,
                        "price_per_luong": gp.price_per_luong,
                        "price_per_gram": gp.price_per_gram,
                        "timestamp": gp.timestamp
                    } for gp in gold_prices_range
                ],
                'save_search_gold': [
                    {
                        "price": rg['price'],
                        "price_per_ounce": rg['price_per_ounce'],
                        "price_per_luong": rg['price_per_luong'],
                        "price_per_gram": rg['price_per_gram'],
                        "timestamp": rg['timestamp']
                    } for rg in rang_cache

                ]
            }
        else:
            raise HTTPException(status_code=404, detail="Không có dữ liệu trong phạm vi ngày đã cho.")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Ngày tháng không hợp lệ. Bạn hãy nhập theo định dạng YYYY-MM-DD.{str(e)} ")
    except Exception as e:
        logging.error(f"Lỗi khi xử lý yêu cầu: {str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi khi xử lý yêu cầu.")

@router.get("/search_data")
async def search_data(date: str, db: Session = Depends(get_db)):
    try:
        try:
            cache_items = redis_client.lrange("Minhdang_list", 0, -1)
            for item in cache_items:
                try:
                    item_data = json.loads(item)
                    if item_data.get('date') == date:
                        logging.info("Dữ liệu đã được thêm vào trong redis")
                        return item_data
                except json.JSONDecodeError:
                    continue
        except Exception as cache_error:
            logging.warning(f"lỗi redis: {str(cache_error)}")
            #//
        database_save = get_data_indatabase(db, date)
        logging.info(f"Lấy dữ liệu từ database: {database_save}")
        if not database_save:
            logging.info("Vào đây là lấy giá trong database")
            try:
                api_data = await fetch_price_api_api(date)
                if api_data:
                    db.add(api_data)
                    db.commit()
                    db.refresh(api_data)
                    database_save = [api_data]
                    logging.info("lấy dữ liệu từ api rồi lưu vào database")
                else:
                    raise HTTPException(status_code=404, detail="Không thể lấy giá vàng từ api")
            except HTTPException as api_error:
                logging.error(f"lỗi api như sau : {str(api_error)}")
                raise api_error
            except Exception as e:
                logging.error(f"lỗi lấy dữ liệu từ API: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Không tìm thấy dữ liệu giá vàng cho ngày này hoặc giá vàng không hợp lệ: {str(e)}")


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
        search_count = crud.increment_search_count(db, date)
        logging.info(f"Search count for {date}: {search_count}")

        if search_count >= 10:
            try:
                json_data = json.dumps(result)
                redis_client.lpush("Minhdang_list", json_data)
                logging.info(f"Lưu dữ liệu vào redis tên key là Minhdang_list: {date}")
            except Exception as cache_error:
                logging.warning(f"Lấy dữ liệu thất bại từ redis: {str(cache_error)}")
        else:
            logging.info(f"Không lưu dữ liệu (search count: {search_count})")

        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"lỗi lấy dữ liệu từ search data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear_redis")
async def clear_redis():
    try:
        all_keys = redis_client.keys("*")
        for key in all_keys:
            redis_client.delete(key)
            logging.info(f"Xóa key: {key}")

        return {"message": f"Xóa thành công {len(all_keys)} keys từ redis"}
    except Exception as e:
        logging.error(f"Lỗi xóa redis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi Xóa redis: {str(e)}")















        # try: # nếu dúng thì chạy vào đây
    #     logging.info("Chạy vào chức năng search_data")
    #
    #     # Tìm trong Redis
    #     danhsach_minhdang = redis_client.lrange("Minhdang_list", 0, -1) # lấy toàn bộ danh sách trong Minhdang_list
    #     for timkiem_gold_save in danhsach_minhdang: # duyệt từng cái một
    #         gold_price_save = json.loads(timkiem_gold_save) # chuyển từng cái đối tượng được lưu từ json thành đối tượng dict các thứ
    #         try: # nếu mà cái gold_price_save truyền key vào mà bằng date người ta nhập vào thì như sau
    #             if gold_price_save['date'] == date:
    #                 logging.info("Data đã được trả về từ Redis")
    #
    #                 # Lấy giá và tính toán
    #                 # lấy cái giá rị của key price để mà tính toán giá vàng
    #                 price = Decimal(str(gold_price_save['price']))  # Convert to Decimal
    #                 # sử lý tính toán các thứ
    #                 price_per_ounce, price_per_luong, price_per_gram = calculate_gold_price(price)
    #
    #                 # Tạo dict với dữ liệu cần lưu
    #                 save_data = { # lưu một cái khuân data để lưu cái gì cần lưu
    #                     "price": price,
    #                     "price_per_ounce": price_per_ounce,
    #                     "price_per_luong": price_per_luong,
    #                     "price_per_gram": price_per_gram
    #                 }
    #
    #                 try: # nếu đúng thì
    #                     # thôi qua crud thì gọi phương thức create , truyền data và save_data vừa có được
    #                     save_search_gold_chill = crud.save_search_gold.create(db=db, data=save_data)
    #                     # sẽ in những cái thông tin này vào database
    #                     logging.info(f"Đã lưu thành công vào database: {save_search_gold_chill}")
    #
    #                     return { # rồi in những cái giá trị của database vừa lưu ra
    #                         "date": gold_price_save['date'],# return cái giá trị lấy về ra
    #                         "price": float(price),#all
    #                         "price_per_ounce": float(price_per_ounce),#all
    #                         "price_per_luong": float(price_per_luong),#all
    #                         "price_per_gram": float(price_per_gram),#all
    #                         "timestamp": save_search_gold_chill.timestamp#all
    #                     }
    #                 except Exception as db_error: # nếu mà thêm vào data lỗi sẽ hiển thị ở đây
    #                     logging.error(f"Lỗi khi lưu vào database: {str(db_error)}")
    #                     raise HTTPException(status_code=500, detail="Lỗi khi lưu dữ liệu vào database")
    #
    #         except Exception as e: # lỗi gì sẽ hiển thị ở đây
    #             logging.error(f"Lỗi khi xử lý dữ liệu Redis: {str(e)}")
    #             continue
    #
    #     # Nếu không tìm thấy dữ liệu
    #     raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho ngày {date}")
    #
    # except Exception as e: # đây cũng thế
    #     logging.error(f"Lỗi trong khi xử lý yêu cầu: {str(e)}")
    #     raise HTTPException(status_code=500, detail="Đã xảy ra lỗi khi xử lý yêu cầu.")