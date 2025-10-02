from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "statistic" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "training_type" VARCHAR(30) NOT NULL,
    "visit_count" INT NOT NULL,
    "star_count" INT NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE NO ACTION
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "statistic";"""
