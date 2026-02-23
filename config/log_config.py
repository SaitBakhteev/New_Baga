import logging

from aiologger import Logger
from aiologger.formatters.base import Formatter
from aiologger.handlers.files import AsyncFileHandler


def setup_logger(module):
    logger = Logger(name=module)
    logger.propagate = False
    for i in [('general', logging.INFO), ('error', logging.ERROR), ('bot', logging.CRITICAL)]:
        handler = AsyncFileHandler(f'logs/{i[0]}.log', encoding='utf-8')
        handler.level = i[1]
        handler.formatter = Formatter('{asctime} - {name} - {levelname} - {message}', style='{')
        logger.add_handler(handler)
    return logger


def setup_sync_logger(module):
    sync_logger = logging.getLogger(name=module)  # отдельный специальный логгер
    for i in [('general.log', 'INFO'), ('error.log', 'ERROR'), ('bot.log', 'CRITICAL')]:
        handler = logging.FileHandler(f'logs/{i[0]}')
        handler.setFormatter(logging.Formatter('{asctime} - {name} - {levelname} - {message}', style='{'))
        handler.setLevel(i[1])
        sync_logger.addHandler(handler)
    return sync_logger


def setup_base_logger():
    # Форматтер для всех хендлеров
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Хендлер для INFO и выше (general.log)
    info_handler = logging.FileHandler('logs/general.log')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # Хендлер для ERROR и выше (error.log)
    error_handler = logging.FileHandler('logs/error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Хендлер для CRITICAL (bot.log)
    critical_handler = logging.FileHandler('logs/bot.log')
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(formatter)

    # Хендлер для консоли
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    logging.basicConfig(
        level=logging.INFO,
        handlers=[info_handler, error_handler, critical_handler, stream_handler]
    )
