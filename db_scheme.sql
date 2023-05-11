-- Table: public.tt_user

-- DROP TABLE IF EXISTS public.tt_user;

CREATE TABLE IF NOT EXISTS public.tt_user
(
    id bigint NOT NULL DEFAULT nextval('tt_user_id_seq'::regclass),
    user_id bigint,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT tt_user_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.tt_user
    OWNER to time_tracker;

-- Table: public.tt_data

-- DROP TABLE IF EXISTS public.tt_data;

CREATE TABLE IF NOT EXISTS public.tt_data
(
    id bigint NOT NULL DEFAULT nextval('tt_data_id_seq'::regclass),
    tt_user_id bigint,
    description text COLLATE pg_catalog."default",
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    event_time timestamp with time zone,
    message_id bigint,
    CONSTRAINT tt_data_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.tt_data
    OWNER to time_tracker;
