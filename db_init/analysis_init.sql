-- ============================================================
-- Analysis Service DB Schema (vitamin_analysis)
-- ============================================================

CREATE TABLE "ans_unit_convertor" (
    "vitamin_name"  VARCHAR(255)   NOT NULL,
    "convert_unit"  NUMERIC(12,8)  NULL,
    CONSTRAINT "PK_ANS_UNIT_CONVERTOR" PRIMARY KEY ("vitamin_name")
);

COMMENT ON COLUMN "ans_unit_convertor"."convert_unit" IS '0.0005';

-- ------------------------------------------------------------

CREATE TABLE "nutrients" (
    "nutrient_id"  BIGSERIAL     NOT NULL,
    "name_ko"      VARCHAR(255)  NULL,
    "name_en"      VARCHAR(255)  NULL,
    "unit"         VARCHAR(20)   NULL,
    "created_at"   TIMESTAMPTZ   NULL DEFAULT now(),
    CONSTRAINT "PK_NUTRIENTS" PRIMARY KEY ("nutrient_id")
);

COMMENT ON COLUMN "nutrients"."unit" IS 'mg, µg, IU 등';

-- ------------------------------------------------------------

CREATE TABLE "nutrient_reference_intake" (
    "ref_id"       BIGSERIAL   NOT NULL,
    "nutrient_id"  BIGINT      NOT NULL,
    "gender"       INTEGER     NULL,
    "age_min"      INTEGER     NULL,
    "age_max"      INTEGER     NULL,
    "rda_amount"   INTEGER     NULL,
    "max_amount"   INTEGER     NULL,
    "created_at"   TIMESTAMPTZ NULL DEFAULT now(),
    "updated_at"   TIMESTAMPTZ NULL,
    CONSTRAINT "PK_NUTRIENT_REFERENCE_INTAKE" PRIMARY KEY ("ref_id"),
    CONSTRAINT "FK_NRI_NUTRIENT" FOREIGN KEY ("nutrient_id") REFERENCES "nutrients" ("nutrient_id")
);

COMMENT ON COLUMN "nutrient_reference_intake"."gender" IS '남:0, 여:1';

-- ------------------------------------------------------------

CREATE TABLE "products" (
    "product_id"      BIGSERIAL    NOT NULL,
    "product_brand"   VARCHAR(255) NOT NULL,
    "product_name"    VARCHAR(255) NOT NULL,
    "serving_per_day" INTEGER      NULL,
    "created_at"      TIMESTAMPTZ  NULL DEFAULT now(),
    "updated_at"      TIMESTAMPTZ  NULL,
    CONSTRAINT "PK_PRODUCTS" PRIMARY KEY ("product_id")
);

-- ------------------------------------------------------------

CREATE TABLE "product_nutrients" (
    "prdt_nutrient_id"   BIGSERIAL  NOT NULL,
    "product_id"         BIGINT     NOT NULL,
    "nutrient_id"        BIGINT     NOT NULL,
    "amount_per_serving" INTEGER    NULL,
    "amount_per_day"     INTEGER    NULL,
    "created_at"         TIMESTAMPTZ NULL DEFAULT now(),
    "updated_at"         TIMESTAMPTZ NULL,
    CONSTRAINT "PK_PRODUCT_NUTRIENTS" PRIMARY KEY ("prdt_nutrient_id"),
    CONSTRAINT "FK_PN_PRODUCT"  FOREIGN KEY ("product_id")  REFERENCES "products"  ("product_id"),
    CONSTRAINT "FK_PN_NUTRIENT" FOREIGN KEY ("nutrient_id") REFERENCES "nutrients" ("nutrient_id")
);

-- ------------------------------------------------------------

CREATE TABLE "analysis_userdata" (
    "cognito_id"             VARCHAR(36)   NOT NULL,
    "ans_birth_dt"           DATE          NULL,
    "ans_gender"             INTEGER       NULL,
    "ans_height"             NUMERIC(5,1)  NULL,
    "ans_weight"             NUMERIC(5,1)  NULL,
    "ans_allergies"          VARCHAR(255)  NULL,
    "ans_chron_diseases"     VARCHAR(255)  NULL,
    "ans_current_conditions" VARCHAR(255)  NULL,
    "created_at"             TIMESTAMPTZ   NULL DEFAULT now(),
    "updated_at"             TIMESTAMPTZ   NULL,
    CONSTRAINT "PK_ANALYSIS_USERDATA" PRIMARY KEY ("cognito_id")
);

COMMENT ON COLUMN "analysis_userdata"."ans_birth_dt"           IS 'YYYY-MM-DD';
COMMENT ON COLUMN "analysis_userdata"."ans_gender"             IS '남:0, 여:1';
COMMENT ON COLUMN "analysis_userdata"."ans_current_conditions" IS '피곤, 스트레스, 수면 등';

-- ------------------------------------------------------------

CREATE TABLE "analysis_result" (
    "result_id"   BIGSERIAL    NOT NULL,
    "cognito_id"  VARCHAR(36)  NOT NULL,
    "summary"     TEXT         NULL,
    "created_at"  TIMESTAMPTZ  NULL DEFAULT now(),
    CONSTRAINT "PK_ANALYSIS_RESULT" PRIMARY KEY ("result_id")
);

-- ------------------------------------------------------------

CREATE TABLE "nutrient_gap" (
    "gap_id"         BIGSERIAL    NOT NULL,
    "nutrient_id"    BIGINT       NOT NULL,
    "result_id"      BIGINT       NOT NULL,
    "cognito_id"     VARCHAR(36)  NOT NULL,
    "current_amount" INTEGER      NULL,
    "gap_amount"     INTEGER      NULL,
    "created_at"     TIMESTAMPTZ  NULL DEFAULT now(),
    CONSTRAINT "PK_NUTRIENT_GAP" PRIMARY KEY ("gap_id"),
    CONSTRAINT "FK_NG_RESULT"   FOREIGN KEY ("result_id")   REFERENCES "analysis_result" ("result_id"),
    CONSTRAINT "FK_NG_NUTRIENT" FOREIGN KEY ("nutrient_id") REFERENCES "nutrients"       ("nutrient_id")
);

COMMENT ON COLUMN "nutrient_gap"."current_amount" IS '복용중/섭취이력 기반';
COMMENT ON COLUMN "nutrient_gap"."gap_amount"     IS '섭취해야 할 양';

-- ------------------------------------------------------------

CREATE TABLE "analysis_supplements" (
    "ans_current_id"         BIGSERIAL    NOT NULL,
    "cognito_id"             VARCHAR(36)  NOT NULL,
    "ans_product_name"       VARCHAR(255) NULL,
    "ans_serving_amount"     INTEGER      NULL,
    "ans_serving_per_day"    INTEGER      NULL,
    "ans_daily_total_amount" INTEGER      NULL,
    "ans_is_active"          BOOLEAN      NULL,
    "ans_ingredients"        JSONB        NULL,
    "created_at"             TIMESTAMPTZ  NULL DEFAULT now(),
    "updated_at"             TIMESTAMPTZ  NULL,
    CONSTRAINT "PK_ANALYSIS_SUPPLEMENTS" PRIMARY KEY ("ans_current_id")
);

COMMENT ON COLUMN "analysis_supplements"."ans_serving_amount"     IS '한번에 2알';
COMMENT ON COLUMN "analysis_supplements"."ans_serving_per_day"    IS '1일 총 3번';
COMMENT ON COLUMN "analysis_supplements"."ans_daily_total_amount" IS '1일 총 6알';
COMMENT ON COLUMN "analysis_supplements"."ans_is_active"          IS '현재복용여부';

-- ------------------------------------------------------------

CREATE TABLE "anaysis_current_ingredients" (
    "ans_ingredient_id"   BIGSERIAL    NOT NULL,
    "ans_current_id"      BIGINT       NOT NULL,
    "cognito_id"          VARCHAR(36)  NULL,
    "ans_ingredient_name" VARCHAR(255) NULL,
    "ans_nutrient_amount" INTEGER      NULL,
    "created_at"          TIMESTAMPTZ  NULL DEFAULT now(),
    CONSTRAINT "PK_ANAYSIS_CURRENT_INGREDIENTS" PRIMARY KEY ("ans_ingredient_id"),
    CONSTRAINT "FK_ACI_SUPPLEMENT" FOREIGN KEY ("ans_current_id") REFERENCES "analysis_supplements" ("ans_current_id")
);

-- ------------------------------------------------------------

CREATE TABLE "recommendations" (
    "rec_id"            BIGSERIAL    NOT NULL,
    "result_id"         BIGINT       NOT NULL,
    "product_id"        BIGINT       NOT NULL,
    "cognito_id"        VARCHAR(36)  NOT NULL,
    "recommend_serving" INTEGER      NULL,
    "rank"              INTEGER      NULL,
    "created_at"        TIMESTAMPTZ  NULL DEFAULT now(),
    CONSTRAINT "PK_RECOMMENDATIONS" PRIMARY KEY ("rec_id"),
    CONSTRAINT "FK_REC_RESULT"  FOREIGN KEY ("result_id")  REFERENCES "analysis_result" ("result_id"),
    CONSTRAINT "FK_REC_PRODUCT" FOREIGN KEY ("product_id") REFERENCES "products"        ("product_id")
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_analysis_result_cognito_id      ON analysis_result (cognito_id);
CREATE INDEX IF NOT EXISTS idx_nutrient_gap_result_id          ON nutrient_gap (result_id);
CREATE INDEX IF NOT EXISTS idx_nutrient_gap_nutrient_id        ON nutrient_gap (nutrient_id);
CREATE INDEX IF NOT EXISTS idx_nutrient_ref_nutrient_id        ON nutrient_reference_intake (nutrient_id);
CREATE INDEX IF NOT EXISTS idx_product_nutrients_product_id    ON product_nutrients (product_id);
CREATE INDEX IF NOT EXISTS idx_product_nutrients_nutrient_id   ON product_nutrients (nutrient_id);
CREATE INDEX IF NOT EXISTS idx_analysis_supplements_cognito_id ON analysis_supplements (cognito_id);
CREATE INDEX IF NOT EXISTS idx_anaysis_ingredients_current_id  ON anaysis_current_ingredients (ans_current_id);
