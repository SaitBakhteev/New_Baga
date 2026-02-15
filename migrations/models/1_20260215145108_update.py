from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "event" ADD "question" TEXT;
        ALTER TABLE "EventUser" ADD "me_liked" INT NOT NULL  DEFAULT 0;
        ALTER TABLE "EventUser" ADD "likes" INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "event" DROP COLUMN "question";
        ALTER TABLE "EventUser" DROP COLUMN "me_liked";
        ALTER TABLE "EventUser" DROP COLUMN "likes";"""
