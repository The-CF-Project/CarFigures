-- upgrade --
ALTER TABLE "carinstance" ADD "locked" TIMESTAMPTZ;
-- downgrade --
ALTER TABLE "carinstance" DROP COLUMN "locked";
