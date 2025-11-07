CREATE TABLE if not exists users(
  id serial PRIMARY KEY, 
  uid integer UNIQUE NOT NULL, 
  cum_min integer NOT NULL DEFAULT 300,
  cum_max integer NOT NULL DEFAULT 600,
  behelp_get integer NOT NULL DEFAULT 250,
  help_get integer NOT NULL DEFAULT 250,
  dick_length integer NOT NULL DEFAULT 100,
  dick_thickness integer NOT NULL DEFAULT 200,
  create_time timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX if not exists users_uid ON users (uid);

CREATE TABLE if not exists cum_history(
  id serial PRIMARY KEY, 
  uid integer NOT NULL, 
  semen integer NOT NULL,
  create_time timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX if not exists cum_history_uid ON cum_history (uid);

CREATE TABLE if not exists help_history(
  id serial PRIMARY KEY, 
  uid integer NOT NULL, 
  semen integer NOT NULL,
  from_uid integer NOT NULL,
  semen_to_from integer NOT NULL,
  create_time timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX if not exists help_history_uid ON help_history (uid);

CREATE TABLE if not exists use_history(
  id serial PRIMARY KEY, 
  uid integer NOT NULL, 
  item integer NOT NULL,
  num integer NOT NULL,
  create_time timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX if not exists use_history_uid ON use_history (uid);

CREATE TABLE if not exists items(
  id serial PRIMARY KEY, 
  name varchar(255) NOT NULL,
  details text NOT NULL
);
