-- upgrade --
ALTER TABLE "carinstance" ADD "event_id" INT;
CREATE TABLE IF NOT EXISTS "event" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "description" VARCHAR(400) NOT NULL,
    "banner" VARCHAR(200) NOT NULL,
    "catch_phrase" VARCHAR(128),
    "start_date" TIMESTAMPTZ NOT NULL,
    "end_date" TIMESTAMPTZ NOT NULL,
    "rarity" DOUBLE PRECISION NOT NULL,
    "union_card" VARCHAR(200) NOT NULL
);
COMMENT ON COLUMN "event"."catch_phrase" IS 'Sentence sent in bonus when someone catches a event card';
COMMENT ON COLUMN "event"."rarity" IS 'Value between 0 and 1, chances of using this event background.';
ALTER TABLE "carinstance" ADD CONSTRAINT "fk_carinst_event_25656e1a" FOREIGN KEY ("event_id") REFERENCES "event" ("id") ON DELETE SET NULL;
-- downgrade --
ALTER TABLE "carinstance" DROP CONSTRAINT "fk_carinst_event_25656e1a";
ALTER TABLE "carinstance" DROP COLUMN "event_id";
DROP TABLE IF EXISTS "event";
