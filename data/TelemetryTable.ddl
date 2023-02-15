CREATE TABLE Workflow (
  uuid STRING(40) NOT NULL,
  creation_time TIMESTAMP NOT NULL,
  recipe STRING(50),
  modules STRING(500),
  preflights_delta INT64,
  setup_delta INT64,
  run_delta INT64,
  total_time INT64,
  metadata STRING(10000)
) PRIMARY KEY (uuid);

CREATE TABLE Telemetry (
  workflow_uuid STRING(40) NOT NULL,
  time TIMESTAMP,
  source_module STRING(50),
  key STRING(50),
  value STRING(50)
) PRIMARY KEY (workflow_uuid, time);
