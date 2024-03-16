-- upgrade --
ALTER TABLE "carinstance" DROP CONSTRAINT "carinstance_trade_player_id_fkey";
ALTER TABLE "carinstance" ADD CONSTRAINT "fk_carinst_player_6b1aca0e" FOREIGN KEY ("trade_player_id") REFERENCES "player" ("id") ON DELETE SET NULL;
-- downgrade --
ALTER TABLE "carinstance" DROP CONSTRAINT "fk_carinst_player_6b1aca0e";
ALTER TABLE "carinstance" ADD CONSTRAINT "carinstance_trade_player_id_fkey" FOREIGN KEY ("trade_player_id") REFERENCES "player" ("id") ON DELETE CASCADE;
