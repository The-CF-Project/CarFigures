-- upgrade --
ALTER TABLE "carinstance" ADD "server_id" BIGINT;
-- downgrade --
ALTER TABLE "carinstance" DROP COLUMN "spawn_time";
