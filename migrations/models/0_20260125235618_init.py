from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "template" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "modified_at" TIMESTAMP NOT NULL,
    "text" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "tg_id" BIGINT NOT NULL UNIQUE,
    "tg_username" VARCHAR(64),
    "tg_name" VARCHAR(150),
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "admin_permissions" INT NOT NULL  DEFAULT 0,
    "receive_notifications" INT NOT NULL  DEFAULT 0,
    "subscription" VARCHAR(64)
);
CREATE TABLE IF NOT EXISTS "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "training_type" VARCHAR(30),
    "created_at" TIMESTAMP NOT NULL,
    "payment_dedline" TIMESTAMP,
    "event_datetime" TIMESTAMP NOT NULL,
    "participants_count" INT NOT NULL  DEFAULT 18,
    "event_text" TEXT,
    "stars" TEXT,
    "boss_id" INT REFERENCES "user" ("id") ON DELETE NO ACTION
);
CREATE TABLE IF NOT EXISTS "EventUser" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "individual_dedline" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "paid_check" INT,
    "paid_check_dedline" TIMESTAMP,
    "payment_confirmed" INT,
    "last_payment_notify" TIMESTAMP,
    "friend" VARCHAR(50),
    "event_id" INT NOT NULL REFERENCES "event" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_EventUser_event_i_4fb903" UNIQUE ("event_id", "user_id")
);
CREATE TABLE IF NOT EXISTS "statistic" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "season_index" INT NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modifed_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "training_type" VARCHAR(30) NOT NULL,
    "visit_count" INT NOT NULL,
    "star_count" INT NOT NULL,
    "likes" INT NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE NO ACTION
);
CREATE TABLE IF NOT EXISTS "voting" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "question" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
