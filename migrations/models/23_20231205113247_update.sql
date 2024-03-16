-- upgrade --
ALTER TABLE "carinstance" ADD "tradeable" BOOL NOT NULL  DEFAULT True;
ALTER TABLE "special" ADD "tradeable" BOOL NOT NULL  DEFAULT True;
-- downgrade --
ALTER TABLE "special" DROP COLUMN "tradeable";
ALTER TABLE "carinstance" DROP COLUMN "tradeable";
