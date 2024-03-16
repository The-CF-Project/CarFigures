-- upgrade --
ALTER TABLE "car" ADD "tradeable" BOOL NOT NULL  DEFAULT True;
-- downgrade --
ALTER TABLE "car" DROP COLUMN "tradeable";
