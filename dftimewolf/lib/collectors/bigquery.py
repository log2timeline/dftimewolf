# -*- coding: utf-8 -*-
"""Reads logs from a BigQuery table."""
from typing import Optional, Type, Union

from google.auth import exceptions as google_auth_exceptions
from google.cloud import bigquery
import google.cloud.exceptions

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib import utils


class BigQueryCollector(module.ThreadAwareModule):
  """Collector for BigQuery."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a GCP logs collector."""
    super(BigQueryCollector, self).__init__(state, name=name, critical=critical)
    self._project_name: str = ''

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
    if query:
      self.StoreContainer(containers.BigQueryQuery(
          query, description, pandas_output))

  def PreProcess(self) -> None:
    """Empty PreProcess."""

  def Process(self, container: containers.BigQueryQuery
              ) -> None:  # pytype: disable=signature-mismatch
    """Collects data from BigQuery.

    Args:
      container: A BigQueryQuery container to execute.
    """

    try:
      if self._project_name:
        bq_client = bigquery.Client(project=self._project_name)
      else:
        bq_client = bigquery.Client()
      df = bq_client.query(container.query).to_dataframe()

    # pytype: disable=module-attr
    except google.cloud.exceptions.NotFound as exception:
      self.ModuleError(f'Error accessing project: {exception!s}',
          critical=True)
    # pytype: enable=module-attr

    except (google_auth_exceptions.DefaultCredentialsError,
            google_auth_exceptions.RefreshError) as exception:
      self.ModuleError(
        'Something is wrong with your gcloud access token or '
        'Application Default Credentials. Try running:\n '
        '$ gcloud auth application-default login'
        )
      self.ModuleError(str(exception), critical=True)

    except Exception as error:  # pylint: disable=broad-except
      self.ModuleError(
          f'Unknown exception encountered: {str(error)}',
          critical=True)

    out_container: Union[containers.DataFrame, containers.File]
    if container.pandas_output:
      out_container = containers.DataFrame(
          df, container.description, container.description)
    else:
      filename = utils.WriteDataFrameToJsonl(df)
      out_container = containers.File(name=container.description, path=filename)
      self.logger.info(f'Downloaded logs to {filename}')

    # Copy metadata from source to output
    out_container.metadata = container.metadata
    self.StoreContainer(out_container)

  def PostProcess(self) -> None:
    """Empty PostProcess."""

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module threads on BigQueryQuery containers."""
    return containers.BigQueryQuery

  def GetThreadPoolSize(self) -> int:
    """Returns the maximum number of threads for this module."""
    return 10  # Arbitrary

  def KeepThreadedContainersInState(self) -> bool:
    """BigQueryQuery containers should not persist after processing."""
    return False

modules_manager.ModulesManager.RegisterModule(BigQueryCollector)
