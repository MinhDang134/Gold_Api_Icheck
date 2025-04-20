from typing import List

from fastapi import APIRouter, Depends, HTTPException # import từ thư viện fastapi impỏt Apirouter để mà thực hiện quản lý các router để quản lý cái luồng chạy dễ hơn
# Depends : giúp chỉ đến tái sử dụng lại code, khi mà một đoạn code nào đó phải dùng trong những router
# HttpException : Thực hiện là khi mà em muốn hiển thị lỗi, hoặc là trang thái của doạn đó em có thể dùng cái này để mà hiển thị lỗi ra
from sqlmodel import Session
# sqlmodel nó là một thư viên, Sesstion là sao thì hiểu đơn gỉản là cái này sẽ giúp em tương tác với api em chỉ cần tạo ra request thôi
# Ví dụ là em đi mua đồ circle k thì em gửi yêu cầu đến nhân viên là làm cái này làm cái kia xong nhân viên sẽ thực hiện yêu cầu của em
# rồi đưa ra cái đồ em mua thì cũng như là gửi request xong nó trả về response
import httpx
# giống như request nhưng mà bất đồng bộ
import json
# thuộc tính json này có thể cho loads và dumps , load từ json thành đối tượng , dumps từ đối tượng thành json
from src.posts.Dependecies import get_db # import getdb
from src.posts.crud import get_data_indatabase

from src.posts.models import GoldPrice
from src.posts.service import get_and_update_gold_price, calculate_gold_price # import nhưng phương thức cần trong service cần dùng
from src.posts import redis_cache, crud # import redis và crud
from datetime import datetime, timedelta # Khai báo thư viện datime để gán dữ liệu các thứ
from decimal import Decimal # khái báo thư viên decimal để làm rõ những số thập phân
import logging # hiển thị ra lỗi
from src.posts.redis_cache import redis_client, get_price_from_cache  # khai báo cái đường dẫn có localhost port va db

router = APIRouter() # Khai báo cái router từ ApiRouter luồng
# Nó sẽ có tác dụng nhóm những router lại thành một cái để dễ xử lý , trong sang bên main mà gọi

# khai báo phương thức post trong router và có kiểu là get_price
@router.post("/get_price/")
# 1 khái báo hàm get_price và db bên trong để quản lý cơ sở dữ liệun
async def get_price(db: Session = Depends(get_db)):
    try:# 2 nếu dúng
        cached_price = redis_cache.get_price_from_cache(redis_cache.redis_client, "gold_price")# gán cached_price
        # 3 để láy giá vàng từ cache nếu có sẽ trả về cached_price , truyền vào là redis và key của nó là gold_price
        api_key = "goldapi-af6o2qsm9f2jcj1-io" # khai báo api
        url = f"https://www.goldapi.io/api/XAU/USD" # khai báo link url

        headers = {
            "x-access-token": api_key # Khai báo phân header
        }

        async with httpx.AsyncClient() as client: #4 async with : có tác dụng là khi xong cái phần này nó sẽ tự đóng
            #4.1 giúp gửi những yêu cầu bất đồng bộ mà không bị đóng app
            price = await get_and_update_gold_price(client, url, headers, cached_price)
            #4.2 truyền các tham số vào gồm client , url , headers , chached_price
            #4.25 bây giờ gán từng giá trị khi truyền price vào cho một hàm khác tính toán rồi trả về lần lượt
            price_per_ounce, price_per_luong, price_per_gram = calculate_gold_price(price)

            # gọi đến phương thưc create tạo bảng và app dữ liệu thông qua class crud và hàm gold_crud và phươngt thực create
            # tac huyền db và dâta vào rồi bên kia sẽ sử lý tự add vào cơ sở dữ liệu
            new_gold_price = crud.gold_crud.create(db, {
                "price": price,
                "price_per_ounce": price_per_ounce,
                "price_per_luong": price_per_luong,
                "price_per_gram": price_per_gram
            })
            # sau khi nhận được dữ liệu rồi thì sẽ in ra giá của cái dữ liệu mới đó
            logging.info(f"Lưu giá vàng vào database: {price}")
            #in ra giá và thời gian cho database
            return {"price": price, "timestamp": new_gold_price.timestamp}

    #43 lỗi thì nhảy vào đây mà hiển thị
    except HTTPException as http_exc:
        logging.error(f"Đã xảy ra lỗi HTTP: {http_exc.detail}")
        raise http_exc
@router.get("/get_price_range/") # hàm này là lấy dữ liệu có trong cache và database để trả về
async def get_price_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try: # nếu đúng
        # Chuyển đổi start_date và end_date thành datetime
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        # Lấy dữ liệu từ cơ sở dữ liệu và Redis
        # gold_price_range gọi đến crud và lấy giá vàng thông qua database khi chuyền db , start và end day vào
        gold_prices_range = crud.get_gold_prices_in_range(db, start_date, end_date) # lấy được giá vàng từ database nếu có ngày đó
        # lấy giá vàng từ cache xem có không thì trả về tham số chuyền vào là server cache redis , key , start và end_date
        rang_cache = redis_cache.rang_save_date_cache(redis_cache.redis_client, 'Minhdang_list', start_date, end_date) # lấy được giá trị từ redis
        print(type(rang_cache))

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
                        "price": rg['price'],
                        "price_per_ounce": rg['price_per_ounce'],
                        "price_per_luong": rg['price_per_luong'],
                        "price_per_gram": rg['price_per_gram'],
                        "timestamp": rg['timestamp']
                    } for rg in rang_cache # đây là do khi duyệt thì rg sẽ trở thành dict lên là sẽ khôg có id cũng như value thì phải truyền key vào

                ]
            }
        else: # nếu mà không tìm thấy dữ liệu nào thi chạy vào đây
            raise HTTPException(status_code=404, detail="Không có dữ liệu trong phạm vi ngày đã cho.")

    except ValueError as e: # nếu có lỗi thì hiển thị ra
        raise HTTPException(status_code=400, detail=f"Ngày tháng không hợp lệ. Bạn hãy nhập theo định dạng YYYY-MM-DD.{str(e)} ")
    except Exception as e: # nếu có lỗi thì hiển thị ra
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

@router.get("/search_data")
async def search_data(date: str, db: Session = Depends(get_db)):
    try:
        # Validate date format
        try:
            kiemtra_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD format")

        # First try to get data from Redis Minhdang_list
        try:
            # Get all items from Minhdang_list
            cache_items = redis_client.lrange("Minhdang_list", 0, -1)
            for item in cache_items:
                try:
                    item_data = json.loads(item)
                    if item_data.get('date') == date:
                        logging.info("Data found in Redis Minhdang_list")
                        return item_data
                except json.JSONDecodeError:
                    continue
        except Exception as cache_error:
            logging.warning(f"Redis cache error: {str(cache_error)}")

        # If not in Redis, query database
        database_save = get_data_indatabase(db, date)
        logging.info(f"Data from database: {database_save}")

        if database_save:
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

            # Increment search count in PostgreSQL
            search_count = crud.increment_search_count(db, date)
            logging.info(f"Search count for {date}: {search_count}")

            if search_count >= 10:
                # Save to Redis Minhdang_list if search count >= 10
                try:
                    # Convert result to JSON string
                    json_data = json.dumps(result)
                    # Add to Minhdang_list
                    redis_client.lpush("Minhdang_list", json_data)
                    logging.info(f"Data saved to Redis Minhdang_list for date: {date}")
                except Exception as cache_error:
                    logging.warning(f"Failed to save to Redis: {str(cache_error)}")
            else:
                logging.info(f"Not saving to Redis yet (search count: {search_count})")

            return result
        else:
            logging.info("No data found in database")
            raise HTTPException(status_code=404, detail="No data found for the specified date")
    except Exception as e:
        logging.error(f"Error in search_data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear_redis")
async def clear_redis():
    try:
        # Lấy danh sách tất cả các key
        all_keys = redis_client.keys("*")
        logging.info(f"Found {len(all_keys)} keys to delete")

        # Xóa từng key
        for key in all_keys:
            redis_client.delete(key)
            logging.info(f"Deleted key: {key}")

        return {"message": f"Successfully deleted {len(all_keys)} keys from Redis"}
    except Exception as e:
        logging.error(f"Error clearing Redis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing Redis: {str(e)}")















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