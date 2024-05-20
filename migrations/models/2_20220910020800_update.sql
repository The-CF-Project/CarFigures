-- upgrade --
ALTER TABLE "carinstance" ALTER COLUMN "trade_player_id" DROP NOT NULL;
-- downgrade --
ALTER TABLE "carinstance" ALTER COLUMN "trade_player_id" SET NOT NULL;
