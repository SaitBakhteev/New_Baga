import os
import traceback
import time
from datetime import datetime
from tortoise.transactions import in_transaction


from config.log_config import setup_logger
from config.constants import redis_client, user_cache
from .models import Product

logger = setup_logger(__name__)


async def create_product(data, products):
    position = data['position']
    title = data['title'] if "title" in data else None
    sale = data['sale'] if "sale" in data else None
    async with in_transaction():
        try:
            if products:
                if position < len(products) - 1:
                    for product in products[position:]:
                        product.position += 1
                    await Product.bulk_update(products[position:], ["position"])
            await Product.create(photo=data['photo'],
                                 title=title,
                                 sale=sale,
                                 position=data['position'],
                                 description=data['description'])
            await _resort_products(products)
            _input_to_redis()

        except Exception as e:
            await logger.error(f'Error on create_product {e}:\n{traceback.format_exc()}')


# Пересортировка продуктов после добавления нового объекта или редактирования позиции
async def _resort_products(products):
    product = await Product.all().order_by('-id').first()
    products.append(product)
    products.sort(key=lambda p: p.position)


# Вставлять в редис значения хешей всех юзеров и установки дедлайна
def _input_to_redis():
    '''
    Функция работает по двум сценариям схеме
    1. Если tg_id юзера изначально нет в кэше,то добавляем
    2. Если tg_id юзера есть в кэше:
        2.1 его дедлайн еще не наступил, то игнорируем
        2.2 дедлайн наступил, т.е. now > dedline, тогда добавляем
      Сценарий 2.2 возможен, если юзер с момента первой записи в кэш до настоящего
    момента не заходил в бот
    :return:
    None
    '''
    now = time.time()
    dedline = now  + 30
    for tg_id in user_cache:
        if not redis_client.hget("promo", tg_id):
            redis_client.hset("promo", tg_id, dedline)
        else:
            old_dedline = redis_client.hget("promo", tg_id)
            if now > old_dedline:
                redis_client.hset("promo", tg_id, dedline)


async def get_all_products():
    return await Product.all().order_by('position')


async def update_product(data, current_index, products):
    product = products[current_index]
    old_photo = product.photo
    new_photo = data.get("photo")
    now = datetime.now()

    async with in_transaction():
        await Product.filter(id=product.id).update(
            title=data.get("title"),
            sale=data.get("sale"),
            description=data.get("description"),
            position=data.get("position"),
            photo=new_photo,
            modified_at=now,
        )
    # Далее это место продолжится только если транзацкяи прошлда успешно?
    # БД зафиксирована → теперь безопасно правим память
    product.title = data.get("title")
    product.sale = data.get("sale")
    product.description = data.get("description")
    product.position = data.get("position")
    product.photo = new_photo
    product.modified_at = now

    # файлы — после успеха БД
    if old_photo and old_photo != new_photo and os.path.exists(old_photo):
        try:
            os.remove(old_photo)
        except OSError as e:
            logger.warning(f"Не удалил старый файл {old_photo}: {e}")

    products.sort(key=lambda p: (p.position is None, p.position or 0))


async def update_position(products, current_index):
    async with in_transaction():
        await products[current_index].save()
        products.sort(key=lambda p: p.position)


async def delete_product(product_id: int, products):
    await Product.filter(id=product_id).delete()
    delete_index = next(i for i, product in enumerate(products) if product.id==product_id)
    os.remove(products[delete_index].photo)
    products.pop(delete_index)
    products.sort(key=lambda p: p.position)
