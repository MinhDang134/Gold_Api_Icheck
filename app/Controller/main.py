from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session
import asyncio
import httpx
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

async def fetch_price_api(client: httpx.AsyncClient, url: str, headers: dict):
    try:
        response = await client.get(url, headers=headers)
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

@app.post("/get_price/")
async def get_price(db: Session = Depends(get_db)):
    try:
        # Kiểm tra cache Redis trước
        cached_price = redis_cache.get_price_from_cache(redis_cache.redis_client, "gold_price")

        api_key = "goldapi-1j04jvsm958fy16-io"  # Thay API key của bạn
        url = f"https://www.goldapi.io/api/XAU/USD"  # Đường dẫn API mới

        headers = {
            "x-access-token": api_key  # Gửi API Key trong header
        }

        async with httpx.AsyncClient() as client:
            if cached_price:
                logging.info("Giá vàng đã được tìm thấy trong bộ nhớ đệm (Redis).")
                price = Decimal(cached_price)

                # Request 1 và chờ 7 giây (được thực hiện đồng thời với request 2)
                task1 = asyncio.create_task(fetch_price_api(client, url, headers))  # Request thứ 1
                await asyncio.sleep(30)  # Ngủ 7 giây

                # Request 2 (được thực hiện song song với task1 khi đang chờ)
                task2 = fetch_price_api(client, url, headers)  # Request thứ 2

                # Đợi kết quả từ cả hai request
                price_from_api1 = await task1  # Kết quả từ request 1
                price_from_api2 = await task2  # Kết quả từ request 2

                # Kiểm tra và xử lý giá vàng từ các API
                if price_from_api1 != price_from_api2:
                    logging.info("Giá vàng từ hai request không trùng nhau. Cập nhật giá mới.")
                    formatted_price = str(price_from_api2)  # Lấy giá từ lần request thứ 2
                    redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price)
                    price = price_from_api2
                else:
                    logging.info(f"Giá vàng từ hai request trùng nhau\ngiá vàng 1 {price_from_api1}\ngiá vàng 2 là {price_from_api2}")
            else:
                # Nếu không có giá trong Redis, gọi API và lưu vào Redis
                price = await fetch_price_api(client, url, headers)
                formatted_price = str(price)
                if redis_cache.save_price_to_cache(redis_cache.redis_client, "gold_price", formatted_price):
                    logging.info(f"Đã lưu thông tin: {formatted_price} vào Redis")
                else:
                    logging.error("Lỗi khi lưu giá vào Redis.")

        # Tính giá vàng theo các đơn vị khác
        ounce_to_gram = Decimal('31.1035')
        luong_to_gram = Decimal('37.5')
        price_per_ounce = price * ounce_to_gram
        price_per_luong = price * luong_to_gram

        # Tạo một bảng ghi giá vàng mới trong database
        new_gold_price = crud.gold_crud.create(db, {
            "price": price,
            "price_per_ounce": price_per_ounce,
            "price_per_luong": price_per_luong,
            "price_per_gram": price
        })

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
