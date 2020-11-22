CREATE TABLE "users" (
  "id" integer PRIMARY KEY,
  "first_name" varchar(35) NOT NULL,
  "last_name" varchar(35) NOT NULL,
  "email" varchar(255) NOT NULL
);

CREATE TABLE "tasks" (
  "id" integer PRIMARY KEY,
  "title" varchar NOT NULL,
  "body" varchar,
  "due" timestamp,
  "reminder" timestamp,
  "user_id" integer
);

CREATE TABLE "groups" (
  "id" integer PRIMARY KEY,
  "name" varchar(20) NOT NULL,
  "description" varchar
);

CREATE TABLE "groups_tasks" (
  "id" integer PRIMARY KEY,
  "group_id" integer NOT NULL,
  "task_id" integer NOT NULL
);

ALTER TABLE "tasks" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "groups_tasks" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "groups_tasks" ADD FOREIGN KEY ("task_id") REFERENCES "tasks" ("id");

COMMENT ON COLUMN "tasks"."user_id" IS 'When user is deleted, remove tasks';
