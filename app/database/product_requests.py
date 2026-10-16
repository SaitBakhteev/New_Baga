import os

from datetime import datetime
from tortoise.transactions import in_transaction
import traceback

from config.log_config import setup_logger
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
        except Exception as e:
            await logger.error(f'Error on create_product {e}:\n{traceback.format_exc()}')

# Пересортировка продуктов после добавления нового объекта или редактирования позиции
async def _resort_products(products):
    product = await Product.all().order_by('-id').first()
    products.append(product)
    products.sort(key=lambda p: p.position)

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