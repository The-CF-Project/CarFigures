-- upgrade --
ALTER TABLE "car" ADD "catch_names" TEXT;
-- downgrade --
ALTER TABLE "car" DROP COLUMN "catch_names";
