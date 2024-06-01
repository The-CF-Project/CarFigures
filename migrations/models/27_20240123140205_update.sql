-- upgrade --
ALTER TABLE "carinstance" ADD "extra_data" JSONB NOT NULL DEFAULT '{}'::JSONB;
-- downgrade --
ALTER TABLE "carinstance" DROP COLUMN "extra_data";