CREATE TABLE Telemetry (
  workflow_uuid STRING(40) NOT NULL,
  time TIMESTAMP,
  source_module STRING(50),
  key STRING(50),
  value STRING(50)
) PRIMARY KEY (workflow_uuid, time);
