# -*- coding: utf-8 -*-
"""Reads logs from a BigQuery table."""
from typing import Optional

from google.auth import exceptions as google_auth_exceptions
from google.cloud import bigquery
import google.cloud.exceptions

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib import utils


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
    self._pandas_output = False

  # pylint: disable=arguments-differ
  def SetUp(self,
            project_name: str,
            query: str,
            description: str,
            pandas_output: bool) -> None:
    """Sets up a BigQuery collector.

    Args:
      project_name (str): name of the project that contains the BigQuery tables.
      query (str): The query to run.
      description (str): A description of the query.
      pandas_output (bool): True if the results should be kept in a pandas DF in
          memory, False if they should be written to disk.
    """
    self._project_name = project_name
    self._query = query
    self._description = description
    self._pandas_output = pandas_output

  def Process(self) -> None:
    """Collects data from BigQuery."""

    try:
      if self._project_name:
        bq_client = bigquery.Client(project=self._project_name)
      else:
        bq_client = bigquery.Client()
      df = bq_client.query(self._query).to_dataframe()

    # pytype: disable=module-attr
    except google.cloud.exceptions.NotFound as exception:
      self.ModuleError(f'Error accessing project: {exception!s}',
          critical=True)
    # pytype: enable=module-attr

    except (google_auth_exceptions.DefaultCredentialsError) as exception:
      self.ModuleError(
        'Something is wrong with your gcloud access token or '
        'Application Default Credentials. Try running:\n '
        '$ gcloud auth application-default login'
        )
      self.ModuleError(exception, critical=True)

    if self._pandas_output:
      frame_container = containers.DataFrame(df, self._description, 'bq_result')
      self.StoreContainer(frame_container)
    else:
      filename = utils.WriteDataFrameToJsonl(df)
      self.PublishMessage(f'Downloaded logs to {filename}')

      bq_report = containers.File(name=self._description, path=filename)
      self.StoreContainer(bq_report)


modules_manager.ModulesManager.RegisterModule(BigQueryCollector)
