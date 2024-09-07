-- upgrade --
ALTER TABLE "car" ADD "album_id" INT;
ALTER TABLE "cartype" ADD "fontspack_id" INT;
ALTER TABLE "exclusive" ADD "fontspack_id" INT;
ALTER TABLE "event" ADD "fontspack_id" INT;

CREATE TABLE IF NOT EXISTS "album" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "emoji" VARCHAR(20) NOT NULL,
    "rebirth_required" INT NOT NULL  DEFAULT 0
);
CREATE TABLE IF NOT EXISTS "goal" (
  "id" SERIAL NOT NULL PRIMARY KEY,
  "name" VARCHAR(64) NOT NULL,
  "player" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
  "car" INTEGER NOT NULL REFERENCES "car" ("id") ON DELETE CASCADE,
  "current" INT NOT NULL  DEFAULT 0,
  "target" INT NOT NULL,
  "completed" BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS "fontspack" (
  "id" SERIAL NOT NULL PRIMARY KEY,
  "name" VARCHAR(64) NOT NULL,
  "title" VARCHAR(200) NOT NULL,
  "capacityn" VARCHAR(200) NOT NULL,
  "capacityd" VARCHAR(200) NOT NULL,
  "stats" VARCHAR(200) NOT NULL,
);
INSERT INTO "fontspack" ("name", "title", "capacityn", "capacityd", "stats") VALUES
  (
  'Standard FontsPack',
  'carfigures/core/imaging/src/fonts/CF-Title.otf',
  'carfigures/core/imaging/src/fonts/CF-CapacityN.otf',
  'carfigures/core/imaging/src/fonts/CF-CapacityD.otf',
  'carfigures/core/imaging/src/fonts/CF-Stats.ttf',
  ),
  (
  'BallsDex FontsPack',
  'carfigures/core/imaging/src/fonts/BD-Title.ttf',
  'carfigures/core/imaging/src/fonts/BD-CapacityN.otf',
  'carfigures/core/imaging/src/fonts/BD-CapacityD.ttf',
  'carfigures/core/imaging/src/fonts/BD-CapacityN.otf',
  );
ALTER TABLE "cartype" ADD CONSTRAINT "fk_cartype_fontspack_2dt54ef5" FOREIGN KEY ("fontspack_id") REFERENCES "fontspack" (id)
ON DELETE CASCADE;
ALTER TABLE "exclusive" ADD CONSTRAINT "fk_exclusive_fontspack_s18jmas1" FOREIGN KEY ("fontspack_id") REFERENCES "fontspack" (id)
ON DELETE CASCADE;
ALTER TABLE "event" ADD CONSTRAINT "fk_event_fontspack_d1md8cwm" FOREIGN KEY ("fontspack_id") REFERENCES "fontspack" (id)
ON DELETE CASCADE;

ALTER TABLE "player" ADD "bolts" INT NOT NULL  DEFAULT 0;
ALTER TABLE "player" ADD "language" SMALLINT NOT NULL  DEFAULT 1;
ALTER TABLE "guildconfig" ADD "language" SMALLINT NOT NULL  DEFAULT 1;
ALTER TABLE "cartype" ADD "icon_position" SMALLINT NOT NULL  DEFAULT 1;

ALTER TABLE "car" ADD CONSTRAINT "fk_car_album_x7f4rlqk" FOREIGN KEY ("album_id") REFERENCES "album" (id) ON DELETE CASCADE;
CREATE TABLE "friendship" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "player1" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "player2" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "bestie" BOOLEAN NOT NULL DEFAULT FALSE,
    "since" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "friendshiprequest" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sender" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "receiver" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE "carinstance" DROP "limited";

CREATE TABLE IF NOT EXISTS "carsuggestion" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "full_name" VARCHAR(48) NOT NULL UNIQUE,
    "cartype" SMALLINT NOT NULL,
    "country" SMALLINT NOT NULL,
    "weight" INT NOT NULL,
    "horsepower" INT NOT NULL,
    "rarity" DOUBLE PRECISION NOT NULL,
    "emoji_id" INT NOT NULL,
    "spawn_picture" VARCHAR(200) NOT NULL,
    "collection_picture" VARCHAR(200) NOT NULL,
    "car_suggester" VARCHAR(64) NOT NULL,
    "image_credits" VARCHAR(64) NOT NULL,
    "capacity_name" VARCHAR(64) NOT NULL,
    "capacity_description" VARCHAR(256) NOT NULL
  );

-- downgrade --
ALTER TABLE "car" DROP CONSTRAINT "fk_car_album_x7f4rlqk";
ALTER TABLE "cartype" DROP CONSTRAINT "fk_cartype_fontspack_2dt54ef5";
ALTER TABLE "exclusive" DROP CONSTRAINT "fk_exclusive_fontspack_s18jmas1";
ALTER TABLE "event" DROP CONSTRAINT "fk_event_fontspack_d1md8cwm";
ALTER TABLE "player" DROP COLUMN "bolts";
ALTER TABLE "guildconfig" DROP COLUMN "language";
ALTER TABLE "player" DROP COLUMN "language";
ALTER TABLE "car" DROP "album_id";
ALTER TABLE "cartype" DROP "fontspack_id";
ALTER TABLE "exclusive" DROP "fontspack_id";
ALTER TABLE "event" DROP "fontspack_id";
DROP TABLE IF EXISTS "goal"
DROP TABLE IF EXISTS "album";
DROP TABLE IF EXISTS "fontspack";
DROP TABLE IF EXISTS "friendship";
DROP TABLE IF EXISTS "friendshiprequest"
DROP TABLE IF EXISTS "carsuggestion"
