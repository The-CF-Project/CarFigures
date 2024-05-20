-- upgrade --
ALTER TABLE "blacklisteduser" ADD "date" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP;
-- downgrade --
ALTER TABLE "blacklisteduser" DROP COLUMN "date";
