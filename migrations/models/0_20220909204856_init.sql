-- upgrade --
CREATE TABLE IF NOT EXISTS "car" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "full_name" VARCHAR(48) NOT NULL UNIQUE,
    "cartype" SMALLINT NOT NULL,
    "country" SMALLINT NOT NULL,
    "weight" INT NOT NULL,
    "horsepower" INT NOT NULL,
    "rarity" DOUBLE PRECISION NOT NULL,
    "emoji_id" INT NOT NULL,
    "spawn_picture" VARCHAR(200) NOT NULL,
    "collection_picture" VARCHAR(200) NOT NULL,
    "credits" VARCHAR(64) NOT NULL,
    "capacity_name" VARCHAR(64) NOT NULL,
    "capacity_description" VARCHAR(256) NOT NULL,
    "capacity_logic" JSONB NOT NULL
);
COMMENT ON COLUMN "car"."cartype" IS 'The CarType of this car';
COMMENT ON COLUMN "car"."country" IS 'The Country of this car';
COMMENT ON COLUMN "car"."weight" IS 'Car weight stat';
COMMENT ON COLUMN "car"."horsepower" IS 'Car horsepower stat';
COMMENT ON COLUMN "car"."rarity" IS 'Rarity of this car';
COMMENT ON COLUMN "car"."emoji_id" IS 'Emoji ID for this car';
COMMENT ON COLUMN "car"."spawn_picture" IS 'Image used when a new car spawns in the wild';
COMMENT ON COLUMN "car"."collection_picture" IS 'Image used when displaying cars';
COMMENT ON COLUMN "car"."credits" IS 'Author of the collection artwork';
COMMENT ON COLUMN "car"."capacity_name" IS 'Name of the carfigure''s capacity';
COMMENT ON COLUMN "car"."capacity_description" IS 'Description of the carfigure''s capacity';
COMMENT ON COLUMN "car"."capacity_logic" IS 'Effect of this capacity';
CREATE TABLE IF NOT EXISTS "guildconfig" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "guild_id" INT NOT NULL UNIQUE,
    "spawn_channel" INT,
    "enabled" BOOL NOT NULL  DEFAULT True
);
COMMENT ON COLUMN "guildconfig"."guild_id" IS 'Discord guild ID';
COMMENT ON COLUMN "guildconfig"."spawn_channel" IS 'Discord channel ID where cars will spawn';
COMMENT ON COLUMN "guildconfig"."enabled" IS 'Whether the bot will spawn carfigures in this guild';
CREATE TABLE IF NOT EXISTS "player" (
    "id" SERIAL NOT NULL PRIMARY KEY,   
    "discord_id" INT NOT NULL UNIQUE
);
COMMENT ON COLUMN "player"."discord_id" IS 'Discord user ID';
CREATE TABLE IF NOT EXISTS "carinstance" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "count" INT NOT NULL,
    "catch_date" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "special" INT NOT NULL  DEFAULT 0,
    "weight_bonus" INT NOT NULL  DEFAULT 0,
    "horsepower_bonus" INT NOT NULL  DEFAULT 0,
    "car_id" INT NOT NULL REFERENCES "car" ("id") ON DELETE CASCADE,
    "player_id" INT NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "trade_player_id" INT NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_carinstanc_player__f154f9" UNIQUE ("player_id", "id")
);
COMMENT ON COLUMN "carinstance"."special" IS 'Defines rare instances, like a limited edition car';
CREATE TABLE IF NOT EXISTS "admin" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "username" VARCHAR(50) NOT NULL UNIQUE,
    "password" VARCHAR(200) NOT NULL,
    "last_login" TIMESTAMPTZ NOT NULL,
    "avatar" VARCHAR(200) NOT NULL  DEFAULT '',
    "intro" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "admin"."last_login" IS 'Last Login';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);