-- upgrade --
ALTER TABLE "blacklisteduser" RENAME COLUMN "discord_id" TO "id";
ALTER TABLE "blacklisteduser" ADD "discord_id" BIGINT NOT NULL UNIQUE;
-- downgrade --
ALTER TABLE "blacklisteduser" RENAME COLUMN "id" TO "discord_id";
ALTER TABLE "blacklisteduser" DROP COLUMN "discord_id";
