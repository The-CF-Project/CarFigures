-- upgrade --
ALTER TABLE "carinstance" ADD "limited" BOOL NOT NULL  DEFAULT False;
ALTER TABLE "carinstance" DROP COLUMN "special";
-- downgrade --
ALTER TABLE "carinstance" ADD "special" INT NOT NULL  DEFAULT 0;
ALTER TABLE "carinstance" DROP COLUMN "limited";
