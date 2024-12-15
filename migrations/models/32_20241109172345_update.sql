-- upgrade --
ALTER TABLE "car" RENAME COLUMN "full_name" TO "fullName";
ALTER TABLE "car" RENAME COLUMN "short_name" TO "shortName";
ALTER TABLE "car" RENAME COLUMN "catch_names" TO "catchNames";
ALTER TABLE "car" RENAME COLUMN "emoji_id" TO "emoji";
ALTER TABLE "car" RENAME COLUMN "spawn_picture" TO "spawnPicture";
ALTER TABLE "car" RENAME COLUMN "collection_picture" TO "collectionPicture";
ALTER TABLE "car" RENAME COLUMN "image_credits" TO "carCredits";
ALTER TABLE "car" RENAME COLUMN "capacity_name" TO "capacityName";
ALTER TABLE "car" RENAME COLUMN "capacity_description" TO "capacityDescription";
ALTER TABLE "car" DROP COLUMN "car_suggester";
ALTER TABLE "car" RENAME COLUMN "created_at" TO "createdAt";
ALTER TABLE "exclusive" RENAME COLUMN "rebirth_required" TO "rebirthRequired";
ALTER TABLE "exclusive" RENAME COLUMN "catch_phrase" TO "catchPhrase";
ALTER TABLE "event" RENAME COLUMN "catch_phrase" TO "catchPhrase";
ALTER TABLE "event" RENAME COLUMN "start_date" TO "startDate";
ALTER TABLE "event" RENAME COLUMN "end_date" TO "endDate";
ALTER TABLE "carinstance" RENAME COLUMN "catch_date" TO "catchDate";
ALTER TABLE "carinstance" RENAME COLUMN "spawned_time" TO "spawnedTime";
ALTER TABLE "carinstance" RENAME COLUMN "server_id" TO "server";
ALTER TABLE "carinstance" RENAME COLUMN "weight_bonus" TO "weightBonus";
ALTER TABLE "carinstance" RENAME COLUMN "horsepower_bonus" TO "horsepowerBonus";
ALTER TABLE "player" RENAME COLUMN "donation_policy" TO "donationPolicy";
ALTER TABLE "player" RENAME COLUMN "privacy_policy" TO "privacyPolicy";
ALTER TABLE "guildconfig" RENAME COLUMN "spawn_channel" TO "spawnChannel";
ALTER TABLE "guildconfig" RENAME COLUMN "spawn_ping" TO "spawnRole";
ALTER TABLE "cartype" ADD "fontsPack_id" INT;
ALTER TABLE "exclusive" ADD "fontsPack_id" INT;
ALTER TABLE "event" ADD "fontsPack_id" INT;
CREATE TABLE IF NOT EXISTS "fontspack" (
  "id" SERIAL NOT NULL PRIMARY KEY,
  "name" VARCHAR(64) NOT NULL,
  "title" VARCHAR(200) NOT NULL,
  "capacityn" VARCHAR(200) NOT NULL,
  "capacityd" VARCHAR(200) NOT NULL,
  "stats" VARCHAR(200) NOT NULL,
  "credits" VARCHAR(200) NOT NULL
);
ALTER TABLE "cartype" ADD CONSTRAINT "fk_cartype_fontspack_2dt54ef5" FOREIGN KEY ("fontsPack_id") REFERENCES "fontspack" (id)
ON DELETE CASCADE;
ALTER TABLE "exclusive" ADD CONSTRAINT "fk_exclusive_fontspack_s18jmas1" FOREIGN KEY ("fontsPack_id") REFERENCES "fontspack" (id)
ON DELETE CASCADE;
ALTER TABLE "event" ADD CONSTRAINT "fk_event_fontspack_d1md8cwm" FOREIGN KEY ("fontsPack_id") REFERENCES "fontspack" (id)
ON DELETE CASCADE;
-- downgrade --
ALTER TABLE "car" RENAME COLUMN "fullName" TO "full_name";
ALTER TABLE "car" RENAME COLUMN "shortName" TO "short_name";
ALTER TABLE "car" RENAME COLUMN "catchNames" TO "catch_names";
ALTER TABLE "car" RENAME COLUMN "emoji" TO "emoji_id";
ALTER TABLE "car" RENAME COLUMN "spawnPicture" TO "spawn_picture";
ALTER TABLE "car" RENAME COLUMN "collectionPicture" TO "collection_picture";
ALTER TABLE "car" RENAME COLUMN "carCredits" TO "image_credits";
ALTER TABLE "car" RENAME COLUMN "capacityName" TO "capacity_name";
ALTER TABLE "car" RENAME COLUMN "capacityDescription" TO "capacity_description";
ALTER TABLE "car" ADD "car_suggester" VARCHAR(64) NOT NULL;
ALTER TABLE "car" RENAME COLUMN "createdAt" TO "created_at";
ALTER TABLE "exclusive" RENAME COLUMN "rebirthRequired" TO "rebirth_required";
ALTER TABLE "exclusive" RENAME COLUMN "catchPhrase" TO "catch_phrase";
ALTER TABLE "event" RENAME COLUMN "catchPhrase" TO "catch_phrase";
ALTER TABLE "event" RENAME COLUMN "startDate" TO "start_date";
ALTER TABLE "event" RENAME COLUMN "endDate" TO "end_date";
ALTER TABLE "carinstance" RENAME COLUMN "catchDate" TO "catch_ate";
ALTER TABLE "carinstance" RENAME COLUMN "spawnedTime" TO "spawned_time";
ALTER TABLE "carinstance" RENAME COLUMN "server" TO "server_id";
ALTER TABLE "carinstance" RENAME COLUMN "weightBonus" TO "weight_bonus";
ALTER TABLE "carinstance" RENAME COLUMN "horsepowerBonus" TO "horsepower_bonus";
ALTER TABLE "player" RENAME COLUMN "donationPolicy" TO "donation_policy";
ALTER TABLE "player" RENAME COLUMN "privacyPolicy" TO "privacy_policy";
ALTER TABLE "guildconfig" RENAME COLUMN "spawnChannel" TO "spawnChannel";
ALTER TABLE "guildconfig" RENAME COLUMN "spawnRole" TO "spawn_ping";
ALTER TABLE "cartype" DROP CONSTRAINT "fk_cartype_fontspack_2dt54ef5";
ALTER TABLE "exclusive" DROP CONSTRAINT "fk_exclusive_fontspack_s18jmas1";
ALTER TABLE "event" DROP CONSTRAINT "fk_event_fontspack_d1md8cwm";
ALTER TABLE "cartype" DROP "fontsPack_id";
ALTER TABLE "exclusive" DROP "fontsPack_id";
ALTER TABLE "event" DROP "fontsPack_id";
DROP TABLE IF EXISTS "fontspack";
