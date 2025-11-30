from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "event" ADD "stars" TEXT;
        ALTER TABLE "event" ADD "training_type" VARCHAR(30);
        CREATE TABLE IF NOT EXISTS "statistic" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "season_index" INT NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modifed_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "training_type" VARCHAR(30) NOT NULL,
    "visit_count" INT NOT NULL,
    "star_count" INT NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE NO ACTION
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "event" DROP COLUMN "stars";
        ALTER TABLE "event" DROP COLUMN "training_type";
        DROP TABLE IF EXISTS "statistic";"""
