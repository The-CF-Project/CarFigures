-- upgrade --
CREATE TABLE IF NOT EXISTS "library" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "topic" VARCHAR(100) NOT NULL,
    "description" VARCHAR(256) NOT NULL,
    "type" SMALLINT NOT NULL  DEFAULT 1,
    "text" TEXT not NULL
);
-- downgrade --
DROP TABLE IF EXISTS "library";
