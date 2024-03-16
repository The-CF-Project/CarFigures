-- upgrade --
ALTER TABLE "carinstance" DROP COLUMN "count";
-- downgrade --
ALTER TABLE "carinstance" ADD "count" INT NOT NULL;
