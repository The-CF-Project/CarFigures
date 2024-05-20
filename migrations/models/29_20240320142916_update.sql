-- upgrade --
ALTER TABLE "carinstance" ADD "spawned_time" TIMESTAMPTZ;
-- downgrade --
ALTER TABLE "carinstance" DROP COLUMN "spawned_time";