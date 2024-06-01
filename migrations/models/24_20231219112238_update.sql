-- upgrade --
ALTER TABLE "event" ADD "hidden" BOOL NOT NULL  DEFAULT False;
-- downgrade --
ALTER TABLE "event" DROP COLUMN "hidden";
