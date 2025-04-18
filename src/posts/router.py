# src/router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import httpx
import json
from typing import Type
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
async def get_price(db: Session = Depends(get_db)): # nó sẽ lấy cái session được định nghĩa trong Dependecies để có thể truy cập dư liệu trong database
    try: # nếu đúng
        #1 gửi key và redis_client sang cho redix
        #3 sau khi mà nhận được dữ liệu từ bên redis hay không thì nó sẽ thực hiện lần lượt như sau
        # và đây là trường hợp nếu đúng
        cached_price = redis_cache.get_price_from_cache(redis_cache.redis_client, "gold_price")# gán cached_price

        api_key = "goldapi-af6o2qsm9f2jcj1-io" # lấy api_key vàng
        url = f"https://www.goldapi.io/api/XAU/USD"# lấy url vàng

        headers = {
            "x-access-token": api_key # lấy header của vàng
        }

        async with httpx.AsyncClient() as client: #4 dùng with và async để khi mà thực hiện xong nó sẽ tự đóng
                        # và httpx.AsyncClient() nó cũng như request trong đồng bộ ấy nó cũng cấp phương thức get,post....
            #5 tiếp tục lấy giá vàng khi chuyền tất cả thông tin cần vào hàm dưới
            price = await get_and_update_gold_price(client, url, headers, cached_price)
            #32 sau khi đã có giá vàng dược return về rồi thì...

            #33 truyền price vào hàm calculate_gold_price để mà cho nó tính tiền
            price_per_ounce, price_per_luong, price_per_gram = calculate_gold_price(price)
            #36 sau khi nhận được giá vàng rồi nó sẽ gán lần lượt cho từng giá trị
            #37 khi này đã có đủ thông tin muốn tạo một value mới thì mình gọi create trong base_crud và truyền dữ liệu vào
            new_gold_price = crud.gold_crud.create(db, {
                "price": price,
                "price_per_ounce": price_per_ounce,
                "price_per_luong": price_per_luong,
                "price_per_gram": price_per_gram
            })
            #41 sau khi nhận được dữ liệu rồi thì sẽ in ra giá của cái dữ liệu mới đó

            logging.info(f"Lưu giá vàng vào database: {price}")
            #42 in ra giá và thời gian cho database
            return {"price": price, "timestamp": new_gold_price.timestamp}

    #43 lỗi thì nhảy vào đây mà hiển thị
    except HTTPException as http_exc:
        logging.error(f"Đã xảy ra lỗi HTTP: {http_exc.detail}")
        raise http_exc
@router.get("/get_price_range/")
async def get_price_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        # Chuyển đổi start_date và end_date thành datetime
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        # Lấy dữ liệu từ cơ sở dữ liệu và Redis
        gold_prices_range = crud.get_gold_prices_in_range(db, start_date, end_date)
        rang_cache = redis_cache.rang_save_date_cache(redis_cache.redis_client, 'Minhdang_list', start_date, end_date)
        chill =json.dumps(rang_cache)
        print(type(chill))

        # Nếu có dữ liệu từ Redis và Database
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
                        "price": rg['price'],  # Truy cập khóa 'price' thay vì thuộc tính
                        "price_per_ounce": rg['price_per_ounce'],  # Truy cập khóa 'price_per_ounce'
                        "price_per_luong": rg['price_per_luong'],  # Truy cập khóa 'price_per_luong'
                        "price_per_gram": rg['price_per_gram'],  # Truy cập khóa 'price_per_gram'
                        "timestamp": rg['timestamp']  # Truy cập khóa 'timestamp'
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


#52 nếu không có thì nó sẽ lấy trong api
        # api_key = "goldapi-af6o2qsm9f2jcj1-io" # lấy key
        # url = "https://www.goldapi.io/api/XAU/USD" # lấy url
        #
        # headers = {# lấy header
        #     "x-access-token": api_key
        # }
        #
        # async with httpx.AsyncClient() as client: #53 tạo một cái để truy xuất post,get,put các thứ tiếp
        #     all_prices = [] #54 tạo một mảng rỗng
        #     current_date = start_date_obj  #55 gán giá trị bắt đầu cho current_date
        #
        #     while current_date <= end_date_obj: #56 nếu mà current_date nhỏ hơn hoặc bằng end_date_obj thì đúng
        #         date_str = current_date.strftime("%Y-%m-%d") #57 thay đổi kiểu dạng dữ liệu
        #         #58 lấy dữ liệu trả về bên trong get_and_update_gold_price
        #         price = await get_and_update_gold_price(client, url, headers, None)
        #         #59 rồi nó cũng sẽ trả về giá rôì dùng cái giá đó thôi
        #
        #         formatted_price = str(price)
        #         new_gold_price = crud.gold_crud.create(db, { #60 tạo một bảng dữ liệu mới cùng create của base_crud
        #             "price": price,
        #             "price_per_ounce": price * Decimal('31.1035'),
        #             "price_per_luong": price * Decimal('37.5'),
        #             "price_per_gram": price
        #         })
        #
        #         all_prices.append({ #62 áp thông tin vào cái mảng rỗng
        #             "date": date_str,
        #             "price": price,
        #             "timestamp": new_gold_price.timestamp
        #         })
        #
        #         current_date += timedelta(days=1) #63 Ví dụ nếu current_date là 2025-01-04, sau khi thực thi câu lệnh này,
        #                                           # giá trị của current_date sẽ là 2025-01-05.
        #
        #     return {"gold_prices": all_prices}#64 in ra cái bảng rỗng đó



@router.get("/search_data", response_model=khung_data)
async def search_data(date: str, db: Session = Depends(get_db)):
    try:
        logging.info("Chạy vào chức năng search_data")

        danhsach_minhdang = redis_client.lrange("Minhdang_list", 0, -1)
        for timkiem_gold_save in danhsach_minhdang:
            gold_price_save = json.loads(timkiem_gold_save)
            try:
                if gold_price_save['date'] == date:
                    print("Data đã được trả về từ Redis")

                    price = gold_price_save['price']
                    price_per_ounce, price_per_luong, price_per_gram = calculate_gold_price(price)

                    # Lưu dữ liệu tìm được vào database
                    save_search_gold_chill = crud.save_search_gold.create(db, {
                        "price": price,
                        "price_per_ounce": price_per_ounce,
                        "price_per_luong": price_per_luong,
                        "price_per_gram": price_per_gram
                    })
                    logging.info(f"Đã lưu thành công vào database: {save_search_gold_chill}")
                    return {"price": price, "timestamp": save_search_gold_chill.timestamp}
            except Exception as e:
                logging.info(f"Lỗi đầu như sau : {str(e)}")

        # Nếu không tìm thấy trong Redis, tìm kiếm trong cơ sở dữ liệu hoặc API
        logging.info("Tìm kiếm trong cơ sở dữ liệu hoặc API nếu không có trong Redis")
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
                logging.info(f"Không tìm thấy dữ liệu cho ngày {date} trong Redis hay cơ sở dữ liệu: {str(e)}")
                raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho ngày {date}.")

    except Exception as e:
        logging.error(f"Lỗi trong khi xử lý yêu cầu: {str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi khi xử lý yêu cầu.")
