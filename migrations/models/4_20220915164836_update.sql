-- upgrade --
ALTER TABLE "carinstance" ADD "favorite" BOOL NOT NULL  DEFAULT False;
-- downgrade --
ALTER TABLE "carinstance" DROP COLUMN "favorite";
