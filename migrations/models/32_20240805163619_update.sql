-- upgrade --
ALTER TABLE "car" ADD "album_id" INT;
CREATE TABLE IF NOT EXISTS "album" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "emoji" VARCHAR(20) NOT NULL,
    "rebirth_required" INT NOT NULL  DEFAULT 0
);

CREATE TABLE IF NOT EXISTS "library" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "description" VARCHAR(256) NOT NULL,
    "type" SMALLINT NOT NULL  DEFAULT 1,
    "text" TEXT not NULL
);

ALTER TABLE "player" ADD "bolts" INT NOT NULL  DEFAULT 0;
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

-- downgrade --
ALTER TABLE "player" DROP COLUMN "bolts";
DROP TABLE IF EXISTS "album";
DROP TABLE IF EXISTS "library";
DROP TABLE IF EXISTS "friendship";
DROP TABLE IF EXISTS "friendshiprequest"
