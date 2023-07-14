"""Processes artifacts using a local plaso process."""
import os
import subprocess
import tempfile
import uuid
from typing import Optional
from typing import Union
from typing import List
import docker

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class LocalPlasoProcessor(module.BaseModule):
  """Processes a list of file paths with Plaso (log2timeline).

  input: A list of file paths to process.
  output: The path to the resulting Plaso storage file.
  """

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str] = None,
      critical: bool = False) -> None:
    super(LocalPlasoProcessor, self).__init__(
        state, name=name, critical=critical)
    self._timezone = None  # type: Optional[str]
    self._output_path = str()
    self._plaso_path = str()
    self._use_docker = False

  def _DeterminePlasoPath(self) -> bool:
    """Checks if log2timeline is somewhere in the user's PATH."""
    for path in os.environ['PATH'].split(os.pathsep):
      full_path = os.path.join(path, 'log2timeline.py')
      if os.path.isfile(full_path):
        self._plaso_path = full_path
        return True
    return False

  def _CheckDockerImage(self) -> bool:
    """Checks if an image is available on the local Docker installation."""
    client = docker.from_env()
    try:
      # Checks if image exists locally, does not pull from registry.
      client.images.get("log2timeline/plaso:latest")
      return True
    except docker.errors.ImageNotFound:
      return False

  def _DockerPlasoRun(
      self, file_container_path: str, command: str, plaso_input_path: str,
      plaso_output_path: str) -> None:
    volumes = {
        file_container_path: {
            'bind': plaso_input_path,
            'mode': 'ro'
        },
        self._output_path: {
            'bind': plaso_output_path,
            'mode': 'rw'
        }
    }
    client = docker.from_env()
    client.containers.run(
        "log2timeline/plaso:latest", volumes=volumes, command=command)

  def _LocalPlasoRun(self, command: List[str]) -> None:
    try:
      l2t_proc = subprocess.Popen(
          command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _, error = l2t_proc.communicate()
      l2t_status = l2t_proc.wait()
    except OSError as exception:
      self.ModuleError(str(exception), critical=True)

    if l2t_status:
      message = (
          'The log2timeline command {0:s} failed: {1!s}.'
          ' Check log file for details.').format(' '.join(command), error)
      self.ModuleError(message, critical=True)

  def SetUp(self, timezone: Optional[str], use_docker: bool) -> None:  # pylint: disable=arguments-differ
    """Sets up the local time zone with Plaso (log2timeline) should use.

    Args:
      timezone: name of the local time zone.
      use_docker: Whether to force usage of the Docker plaso image or not.
    """
    self._timezone = timezone
    self._output_path = tempfile.mkdtemp()
    if use_docker:
      if not self._CheckDockerImage():
        self.ModuleError(
            'Docker image log2timeline/plaso not found. To fix: \n'
            '  "docker pull log2timeline/plaso"',
            critical=True)
      self._use_docker = True
    elif not self._DeterminePlasoPath():
      self.ModuleError(
          'Could not run log2timeline.py from PATH or a local '
          'Docker image. To fix: \n'
          '  "apt install plaso-tools" or "docker pull '
          'log2timeline/plaso"',
          critical=True)

  def _processContainer(
      self, container: Union[containers.File, containers.Directory]) -> None:
    """ Processes a given container either File or Directory

    Args:
      container: Container to be processed.
    """
    description = container.name
    path = container.path
    if self._use_docker:
      plaso_output_dir = '/data/output'
      plaso_input_dir = '/data/input'
    else:
      plaso_output_dir = self._output_path
      plaso_input_dir = container.path

    log_file_path = os.path.join(plaso_output_dir, 'plaso.log')

    # Build the plaso command line.
    if self._use_docker:
      cmd = ['log2timeline']
    else:
      cmd = [self._plaso_path]

    # Since we might be running alongside another Module, always disable
    # the status view.
    cmd.extend(['-q', '--status_view', 'none'])
    if self._timezone:
      cmd.extend(['-z', self._timezone])

    # Analyze all available partitions.
    cmd.extend(['--partition', 'all'])

    # Setup logging.
    cmd.extend(['--logfile', log_file_path])

    # And now, the crux of the command.
    # Generate a new storage file for each plaso run
    plaso_output_file = '{0:s}.plaso'.format(uuid.uuid4().hex)
    plaso_output_path = os.path.join(plaso_output_dir, plaso_output_file)
    cmd.extend(['--storage-file', plaso_output_path, plaso_input_dir])

    plaso_storage_file_path = os.path.join(self._output_path, plaso_output_file)

    self.logger.info('Log file: {0:s}'.format(plaso_storage_file_path))

    # Run the l2t command
    full_cmd = ' '.join(cmd)
    self.logger.info('Running external command: "{0:s}"'.format(full_cmd))
    if self._use_docker:
      self._DockerPlasoRun(path, full_cmd, plaso_input_dir, plaso_output_dir)
    else:
      self._LocalPlasoRun(cmd)

    new_container = containers.File(description, plaso_storage_file_path)
    self.StoreContainer(new_container)

  def Process(self) -> None:
    """Executes log2timeline.py on the module input."""

    combined_list = [
    ]  # type: List[Union[containers.File, containers.Directory]]
    for file_container in self.GetContainers(containers.File, pop=True):
      combined_list.append(file_container)

    for directory_container in self.GetContainers(containers.Directory,
                                                        pop=True):
      combined_list.append(directory_container)

    for item in combined_list:
      self._processContainer(item)


modules_manager.ModulesManager.RegisterModule(LocalPlasoProcessor)
