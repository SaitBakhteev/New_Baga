from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "event" ADD "training_type" VARCHAR(30);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "event" DROP COLUMN "training_type";"""
