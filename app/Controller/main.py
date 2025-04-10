from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session
import requests
import logging
from app.Model import database
from app.Controller import crud
from app.Model import redis_cache
from decimal import Decimal


app = FastAPI()
logging.basicConfig(level=logging.INFO)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/get_price/")
def get_price(db: Session = Depends(get_db)):
    try:
        # Kiểm tra cache Redis trước
        cached_price = redis_cache.get_price_from_cache(redis_cache.redis_client, "gold_price")

        api_key = "goldapi-1j04jvsm958fy16-io"  # Thay API key của bạn
        url = f"https://www.goldapi.io/api/XAU/USD"  # Đường dẫn API mới

        headers = {
            "x-access-token": api_key  # Gửi API Key trong header
        }

        if cached_price:
            logging.info("Giá vàng đã được tìm thấy trong bộ nhớ đệm (Redis).")
            price = Decimal(cached_price)

            # Kiểm tra xem giá vàng trong cache có trùng với giá vàng từ API không
            try:
                response = requests.get(url, headers=headers)
                logging.info(f"Trạng thái API: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    price_per_ounce = data['price']

                    if price_per_ounce:
                        price_from_api = Decimal(price_per_ounce)
                        if price_from_api != price:
                            logging.info("Giá vàng trong Redis không trùng với giá từ API, lấy giá từ API.")
                            # Nếu giá từ API khác với giá trong cache, lưu giá từ API vào Redis
                            formatted_price = str(price_from_api)
                            redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price)
                            price = price_from_api
                        else:
                            logging.info("Giá vàng trong Redis trùng với giá từ API.")
                    else:
                        logging.error("Nhận được dữ liệu không hợp lệ từ API.")
                        raise HTTPException(status_code=500, detail="Dữ liệu không hợp lệ từ API.")
                else:
                    logging.error(f"API trả về lỗi: {response.status_code}")
                    raise HTTPException(status_code=500, detail="Không thể lấy dữ liệu từ API.")
            except Exception as e:
                logging.error(f"Lỗi khi gọi API: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Lỗi khi gọi API: {str(e)}")

        else:
            # Nếu không có giá trong Redis, gọi API và lưu vào Redis
            try:
                response = requests.get(url, headers=headers)
                logging.info(f"Trạng thái API: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    price_per_ounce = data['price']

                    if price_per_ounce:
                        price = Decimal(price_per_ounce)
                        formatted_price = str(price_per_ounce)

                        # Lưu giá trị vào Redis Cache với TTL (thời gian sống) là 1 giờ (3600 giây)
                        if redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price):
                            logging.info(f"Đã lưu thông tin: {formatted_price} vào Redis")
                        else:
                            logging.error("Lỗi khi lưu giá vào Redis.")
                    else:
                        logging.error("Nhận được dữ liệu không hợp lệ từ API.")
                        raise HTTPException(status_code=500, detail="Dữ liệu không hợp lệ từ API.")
                else:
                    logging.error(f"API trả về lỗi: {response.status_code}")
                    raise HTTPException(status_code=500, detail="Không thể lấy dữ liệu từ API.")
            except Exception as e:
                logging.error(f"Lỗi khi gọi API: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Lỗi khi gọi API: {str(e)}")

        # Tính giá vàng theo các đơn vị khác
        ounce_to_gram = Decimal('31.1035')
        luong_to_gram = Decimal('37.5')
        price_per_ounce = price * ounce_to_gram
        price_per_luong = price * luong_to_gram

        # Tạo một bảng ghi giá vàng mới trong database
        new_gold_price = crud.create_gold_price(
            db=db,
            price=price,
            price_per_ounce=price_per_ounce,
            price_per_luong=price_per_luong,
            price_per_gram=price
        )

        logging.info(f"Lưu giá vàng vào database: {price}")
        return {"price": price, "timestamp": new_gold_price.timestamp}

    except HTTPException as http_exc:
        logging.error(f"Đã xảy ra lỗi HTTP: {http_exc.detail}")
        raise http_exc


@app.get("/get_price_range/")
def get_price_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        start_dates = start_date
        end_dates = end_date
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Ngày tháng không hợp lệ. Bạn hãy nhập theo định dạng YYYY-MM-DD.")

    gold_prices_range = crud.get_gold_prices_in_range(db, start_dates, end_dates)

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
