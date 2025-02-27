"""Processes artifacts using OpenRelik."""

import time

from typing import Type, Iterator

from openrelik_api_client import api_client, folders, workflows

from dftimewolf.lib import module
from dftimewolf.lib import state as state_lib
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager


# pylint: disable=no-member
class OpenRelikProcessor(module.ThreadAwareModule):
  """Processes artifacts with OpenRelik."""

  def __init__(
    self,
    state: state_lib.DFTimewolfState,
    name: str | None = None,
    critical: bool = False,
  ) -> None:
    """Initializes an OpenRelik processor.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super().__init__(state=state, name=name, critical=critical)
    self.openrelik_api_client: api_client.APIClient = None
    self.openrelik_folder_client: folders.FoldersAPI = None
    self.openrelik_workflow_client: workflows.WorkflowsAPI = None
    self.openrelik_api: str | None = None
    self.openrelik_ui: str | None = None
    self.openrelik_api_key: str | None = None
    self.template_workflow_id: int | None = None
    self.folder_id: int | None = None
    self.incident_id: str | None = None

  # pylint: disable=arguments-differ
  def SetUp(
    self,
    incident_id: str | None,
    folder_id: int | None,
    template_workflow_id: int | None,
    openrelik_api: str | None,
    openrelik_ui: str | None,
    openrelik_api_key: str | None,
  ) -> None:
    self.openrelik_api = openrelik_api
    self.openrelik_ui = openrelik_ui
    self.openrelik_api_key = openrelik_api_key
    self.openrelik_api_client = api_client.APIClient(
      self.openrelik_api, self.openrelik_api_key
    )
    self.openrelik_folder_client = folders.FoldersAPI(self.openrelik_api_client)
    self.openrelik_workflow_client = workflows.WorkflowsAPI(
      self.openrelik_api_client
    )
    self.folder_id = folder_id
    self.template_workflow_id = template_workflow_id
    self.incident_id = incident_id
    if not self.folder_id or not self.openrelik_folder_client.folder_exists(
      self.folder_id
    ):
      self.folder_id = self.openrelik_folder_client.create_root_folder(
        f"{self.incident_id}"
      )
      self.logger.info(f"Created folder {self.folder_id}")
    self.logger.info(f"Updating folder {self.folder_id}")
    self.openrelik_folder_client.update_folder(
      self.folder_id, {"display_name": self.incident_id}
    )

  def PollWorkflowStatus(self, workflow_id: int) -> Iterator[str | None]:
    """Polls the status of a workflow until it completes."""

    filename = str(workflow_id)
    workflow = self.openrelik_workflow_client.get_workflow(
      self.folder_id, workflow_id
    )
    status = None
    tasks = workflow.get("tasks")
    if tasks and len(tasks) > 0:
      status = tasks[0].get("status_short")
    if not status:
      self.ModuleError("Error polling workflow status", critical=True)
    self.logger.info(f"Waiting for workflow {workflow_id} to finish.")
    output_file_ids = {}
    while status not in ("SUCCESS", "FAILURE"):
      self.logger.debug(f"Workflow {workflow_id} status: {status}")
      time.sleep(15)
      workflow = self.openrelik_workflow_client.get_workflow(
        self.folder_id, workflow_id
      )
      tasks = workflow.get("tasks")
      if tasks:
        status = tasks[0].get("status_short")
    self.logger.debug(f"Workflow {workflow_id} status: {status}")
    if status == "FAILURE":
      self.ModuleError(f"Workflow {workflow_id} failed", critical=True)

    for task in tasks:
      output_files = task.get("output_files", [])
      for output_file in output_files:
        output_file_id = output_file.get("id")
        filename = output_file.get("display_name", workflow_id)
        output_file_ids[output_file_id] = filename

    for output_file_id, filename in output_file_ids.items():
      local_path = self.DownloadWorkflowOutput(output_file_id, filename)
      yield local_path

  def DownloadWorkflowOutput(self, file_id: int, filename: str) -> str | None:
    """Downloads a file from OpenRelik.

    Args:
        file_id: The ID of the file to download.
        filename: The name of the file to download.

    Returns:
        str: The path to the downloaded file.
    """
    self.logger.info(f"Downloading {filename}, ID:{file_id}")
    local_path: str = self.openrelik_api_client.download_file(file_id, filename)
    if not local_path:
      self.logger.error(f"Failed to download {filename}, ID:{file_id}")
      return None
    self.PublishMessage(f"Saved output for file ID {file_id} to {local_path}")
    return local_path

  def Process(
    self, container: containers.File
  ) -> None:  # pytype: disable=signature-mismatch
    file_ids = []
    self.logger.info(f"Uploading file {container.path}")
    file_id = self.openrelik_api_client.upload_file(
      container.path, self.folder_id
    )
    if file_id:
      self.logger.info(f"Uploaded file {container.path}")
      file_ids.append(file_id)

    workflow_id = self.openrelik_workflow_client.create_workflow(
      self.folder_id, file_ids, self.template_workflow_id
    )
    workflow_url = f"{self.openrelik_ui}/folder/{self.folder_id}"
    self.PublishMessage(
      f"New workflow ID {workflow_id} can be viewed at: {workflow_url}"
    )
    self.openrelik_workflow_client.run_workflow(self.folder_id, workflow_id)

    for local_path in self.PollWorkflowStatus(workflow_id):
      if local_path:
        fs_container = containers.File(path=local_path, name=local_path)
        self.StreamContainer(fs_container)

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.File

  def GetThreadPoolSize(self) -> int:
    return 3

  @staticmethod
  def KeepThreadedContainersInState() -> bool:
    return False

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(OpenRelikProcessor)
