-- upgrade --
CREATE TABLE IF NOT EXISTS "blacklisteduser" (
    "discord_id" BIGSERIAL NOT NULL PRIMARY KEY
);
COMMENT ON COLUMN "blacklisteduser"."discord_id" IS 'Discord user ID';
-- downgrade --
DROP TABLE IF EXISTS "blacklisteduser";
