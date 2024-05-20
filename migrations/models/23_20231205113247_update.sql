-- upgrade --
ALTER TABLE "carinstance" ADD "tradeable" BOOL NOT NULL  DEFAULT True;
ALTER TABLE "event" ADD "tradeable" BOOL NOT NULL  DEFAULT True;
-- downgrade --
ALTER TABLE "event" DROP COLUMN "tradeable";
ALTER TABLE "carinstance" DROP COLUMN "tradeable";
