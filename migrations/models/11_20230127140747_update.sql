-- upgrade --
ALTER TABLE "blacklisteduser" ADD "reason" TEXT;
-- downgrade --
ALTER TABLE "blacklisteduser" DROP COLUMN "reason";
