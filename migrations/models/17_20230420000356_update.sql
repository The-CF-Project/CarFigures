-- upgrade --
ALTER TABLE "event" ADD "emoji" VARCHAR(20);
-- downgrade --
ALTER TABLE "event" DROP COLUMN "emoji";
