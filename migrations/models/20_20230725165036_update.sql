-- upgrade --
ALTER TABLE "car" ADD "country_id" INT;
ALTER TABLE "car" ADD "cartype_id" INT; -- Add NOT NULL after we filled the table --
CREATE TABLE IF NOT EXISTS "country" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "image" VARCHAR(200) NOT NULL
);
COMMENT ON COLUMN "car"."country_id" IS 'The Country of this car';
COMMENT ON COLUMN "car"."cartype_id" IS 'The CarType of this car';
COMMENT ON COLUMN "country"."image" IS '512x512 PNG image';;
CREATE TABLE IF NOT EXISTS "cartype" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "image" VARCHAR(200) NOT NULL
);
COMMENT ON COLUMN "cartype"."image" IS '1428x2000 PNG image';
ALTER TABLE "event" ADD "card" VARCHAR(200);
UPDATE "event" SET "card" = "union_card";
ALTER TABLE "event" DROP COLUMN "union_card";
ALTER TABLE "car" ADD CONSTRAINT "fk_car_cartype_d7fd92a9" FOREIGN KEY ("cartype_id") REFERENCES "cartype" ("id") ON DELETE CASCADE;
ALTER TABLE "car" ADD CONSTRAINT "fk_car_country_cfe9c5c3" FOREIGN KEY ("country_id") REFERENCES "country" ("id") ON DELETE SET NULL;
INSERT INTO "country" ("name", "image") VALUES
    ('China', '/carfigures/core/image_generator/src/china.png'),
    ('France', '/carfigures/core/image_generator/src/france.png'),
    ('Germany', '/carfigures/core/image_generator/src/germany.png'),
    ('Italy', '/carfigures/core/image_generator/src/italy.png'),
    ('Japan', '/carfigures/core/image_generator/src/japan.png'),
    ('South-Korea', '/carfigures/core/image_generator/src/southkorea.png'),
    ('Sweden', '/carfigures/core/image_generator/src/sweden.png'),
    ('United-Kingdom', '/carfigures/core/image_generator/src/unitedkingdom.png'),
    ('United-States', '/carfigures/core/image_generator/src/unitedstates.png');
INSERT INTO "cartype" ("name", "image") VALUES
    ('Union', '/carfigures/core/image_generator/src/union.png');
UPDATE "car" SET "country_id" = "country" WHERE "country" != 3;
UPDATE "car" SET "country_id" = null WHERE "country" = 3;
UPDATE "car" SET "cartype_id" = "cartype";
ALTER TABLE "car" ALTER COLUMN "cartype_id" SET NOT NULL; -- Table filled, now we can put non-nullable constraint --
ALTER TABLE "car" DROP COLUMN "country";
ALTER TABLE "car" DROP COLUMN "cartype";
-- downgrade --
ALTER TABLE "car" DROP CONSTRAINT "fk_car_country_cfe9c5c3";
ALTER TABLE "car" DROP CONSTRAINT "fk_car_cartype_d7fd92a9";
ALTER TABLE "car" ADD "cartype" SMALLINT;
ALTER TABLE "car" ADD "country" SMALLINT;
UPDATE "car" SET "cartype" = "cartype_id";
UPDATE "car" SET "country" = "country_id";
ALTER TABLE "car" DROP COLUMN "country_id";
ALTER TABLE "car" DROP COLUMN "cartype_id";
ALTER TABLE "event" ADD "union_card" VARCHAR(200);
ALTER TABLE "event" DROP COLUMN "card";
DROP TABLE IF EXISTS "country";
DROP TABLE IF EXISTS "cartype";
ALTER TABLE "car" ALTER COLUMN "cartype" SET NOT NULL;
ALTER TABLE "car" ALTER COLUMN "cartype" SET NOT NULL;

