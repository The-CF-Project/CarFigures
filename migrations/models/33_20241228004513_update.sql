-- upgrade --
CREATE TABLE "friendship" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "friender" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "friended" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "bestie" BOOLEAN NOT NULL DEFAULT FALSE,
    "since" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE "car" ADD "fontsMetaData" JSONB NOT NULL DEFAULT '{}'::JSONB;
ALTER TABLE "car" ADD "optionalCard" VARCHAR(200);
ALTER TABLE "player" ADD "bolts" INT NOT NULL  DEFAULT 0;
ALTER TABLE "cartype" ADD "rebirthRequired" INT NOT NULL  DEFAULT 0;

CREATE TABLE "friendshiprequest" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sender" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "receiver" INTEGER NOT NULL REFERENCES "player" ("id") ON DELETE CASCADE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- downgrade --
ALTER TABLE "player" DROP COLUMN "bolts";
ALTER TABLE "cartype" DROP COLUMN "rebirthRequired";
ALTER TABLE "car" DROP COLUMN "fontsMetaData";
ALTER TABLE "car" DROP COLUMN "optionalCard";
DROP TABLE IF EXISTS "friendship";
DROP TABLE IF EXISTS "friendshiprequest";
