from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "statistic" ADD "season_index" INT NOT NULL  DEFAULT 0;
        ALTER TABLE "statistic" ADD "modifed_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "statistic" ADD "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "statistic" DROP COLUMN "season_index";
        ALTER TABLE "statistic" DROP COLUMN "modifed_at";
        ALTER TABLE "statistic" DROP COLUMN "created_at";"""
