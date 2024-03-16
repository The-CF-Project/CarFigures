-- upgrade --
ALTER TABLE "car" ADD "short_name" VARCHAR(20);
-- downgrade --
ALTER TABLE "car" DROP COLUMN "short_name";
