-- upgrade --
ALTER TABLE "car" ADD "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP;
UPDATE car c
SET created_at = ci.catch_date
FROM (
  SELECT car_id, MIN(catch_date) AS catch_date
  FROM carinstance
  GROUP BY car_id
) AS ci
WHERE c.id = ci.car_id;
-- downgrade --
ALTER TABLE "car" DROP COLUMN "created_at";