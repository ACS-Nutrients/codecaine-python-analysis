CREATE TABLE "purchase_history" (
	"purchase_id"	BIGSERIAL		NOT NULL,
	"item_id"	BIGSERIAL		NOT NULL,
	"cognito_id"	VARCHAR(36)		NOT NULL,
	"purchased_dt"	DATE		NULL,
	"total_quantity"	INTEGER		NULL,
	"remain_day"	INTEGER		NULL,
	"reminder_sent"	BOOLEAN		NULL,
	"created_at"	TIMESTAMPTZ		NULL,
	"updated_at"	TIMESTAMPTZ		NULL
);

COMMENT ON COLUMN "purchase_history"."cognito_id" IS 'PK';

COMMENT ON COLUMN "purchase_history"."purchased_dt" IS 'YYYY-MM-DD';

COMMENT ON COLUMN "purchase_history"."total_quantity" IS '100알';

COMMENT ON COLUMN "purchase_history"."remain_day" IS '25일';

COMMENT ON COLUMN "purchase_history"."reminder_sent" IS 'TRUE=발송';

CREATE TABLE "intake_item" (
	"item_id"	BIGSERIAL		NOT NULL,
	"cognito_id"	VARCHAR(36)		NOT NULL,
	"intake_dt"	DATE		NULL,
	"created_at"	TIMESTAMPTZ		NULL
);

COMMENT ON COLUMN "intake_item"."cognito_id" IS 'PK';

COMMENT ON COLUMN "intake_item"."intake_dt" IS 'YYYY-MM-DD';

COMMENT ON COLUMN "intake_item"."created_at" IS '섭취한 시각';

CREATE TABLE "intake_supplements" (
	"cognito_id"	VARCHAR(36)		NOT NULL,
	"itk_product_name"	VARCHAR(255)		NULL,
	"itk_serving_amount"	INTEGER		NULL,
	"itk_serving_per_day"	INTEGER		NULL,
	"itk_daily_total_amount"	INTEGER		NULL,
	"itk_total_quantity"	INTEGER		NULL,
	"is_active"	BOOLEAN		NULL,
	"itk_purchased_dt"	DATE		NULL,
	"itk_estimated_end_dt"	DATE		NULL,
	"created_at"	TIMESTAMPTZ		NULL,
	"updated_at"	TIMESTAMPTZ		NULL
);

COMMENT ON COLUMN "intake_supplements"."cognito_id" IS 'PK';

COMMENT ON COLUMN "intake_supplements"."itk_serving_amount" IS '한번에 2알';

COMMENT ON COLUMN "intake_supplements"."itk_serving_per_day" IS '1일 총 3번';

COMMENT ON COLUMN "intake_supplements"."itk_daily_total_amount" IS '1일 총 6알';

COMMENT ON COLUMN "intake_supplements"."itk_total_quantity" IS '총 60알';

COMMENT ON COLUMN "intake_supplements"."is_active" IS '현재복용여부';

COMMENT ON COLUMN "intake_supplements"."itk_purchased_dt" IS 'YYYY-MM-DD';

COMMENT ON COLUMN "intake_supplements"."itk_estimated_end_dt" IS 'YYYY-MM-DD';

ALTER TABLE "purchase_history" ADD CONSTRAINT "PK_PURCHASE_HISTORY" PRIMARY KEY (
	"purchase_id",
	"item_id",
	"cognito_id"
);

ALTER TABLE "intake_item" ADD CONSTRAINT "PK_INTAKE_ITEM" PRIMARY KEY (
	"item_id",
	"cognito_id"
);

ALTER TABLE "intake_supplements" ADD CONSTRAINT "PK_INTAKE_SUPPLEMENTS" PRIMARY KEY (
	"cognito_id"
);

ALTER TABLE "purchase_history" ADD CONSTRAINT "FK_intake_item_TO_purchase_history_1" FOREIGN KEY (
	"item_id"
)
REFERENCES "intake_item" (
	"item_id"
);

ALTER TABLE "intake_item" ADD CONSTRAINT "FK_intake_supplements_TO_intake_item_1" FOREIGN KEY (
	"cognito_id"
)
REFERENCES "intake_supplements" (
	"cognito_id"
);