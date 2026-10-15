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
