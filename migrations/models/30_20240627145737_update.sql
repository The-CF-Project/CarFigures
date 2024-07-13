-- upgrade --
ALTER TABLE "player" ADD "rebirths" INT NOT NULL  DEFAULT 0;
-- downgrade --
ALTER TABLE "player" DROP COLUMN "rebirths";
