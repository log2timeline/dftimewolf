CREATE TABLE Telemetry (
  workflow_uuid STRING(40) NOT NULL,
  time TIMESTAMP,
  recipe STRING(50),
  source_module STRING(50),
  key STRING(100),
  value STRING(5000)
) PRIMARY KEY (workflow_uuid, time);
