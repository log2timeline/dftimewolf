# -*- coding: utf-8 -*-
"""Reads logs from a BigQuery table."""
import tempfile
from typing import Optional

from google.auth import exceptions as google_auth_exceptions
import google.cloud.bigquery as bigquery
import google.cloud.exceptions

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class BigQueryCollector(module.BaseModule):
  """Collector for BigQuery."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a GCP logs collector."""
    super(BigQueryCollector, self).__init__(state, name=name, critical=critical)
    self._project_name = ""
    self._query = ""
    self._description = ""

  # pylint: disable=arguments-differ
  def SetUp(self, project_name: str, query: str, description: str) -> None:
    """Sets up a BigQuery collector.

    Args:
      project_name (str): name of the project that contains the BigQuery tables.
      query (str): The query to run.
      description (str): A description of the query.
    """
    self._project_name = project_name
    self._query = query
    self._description = description

  def Process(self) -> None:
    """Collects data from BigQuery."""
    output_file = tempfile.NamedTemporaryFile(
        mode="w", delete=False, encoding="utf-8", suffix=".jsonl")
    output_path = output_file.name
    self.logger.info("Downloading results to {0:s}".format(output_path))

    try:
      if self._project_name:
        bq_client = bigquery.Client(project=self._project_name)
      else:
        bq_client = bigquery.Client()

      records = bq_client.query(self._query).to_dataframe().to_json(
          orient="records", lines=True, date_format="iso")
      output_file.write(records)

    except google.cloud.exceptions.NotFound as exception:  # pytype: disable=module-attr
      self.ModuleError(f"Error accessing project: {exception!s}",
          critical=True)

    except (google_auth_exceptions.DefaultCredentialsError) as exception:
      self.ModuleError(
        "Something is wrong with your gcloud access token or "
        "Application Default Credentials. Try running:\n "
        "$ gcloud auth application-default login"
        )
      self.ModuleError(exception, critical=True)

    self.logger.success(f"Downloaded logs to {output_path}")
    output_file.close()

    bq_report = containers.File(name=self._description, path=output_path)
    self.state.StoreContainer(bq_report)


modules_manager.ModulesManager.RegisterModule(BigQueryCollector)
