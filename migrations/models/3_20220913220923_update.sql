-- upgrade --
ALTER TABLE "car" ADD "enabled" BOOL NOT NULL  DEFAULT True;
-- downgrade --
ALTER TABLE "car" DROP COLUMN "enabled";
