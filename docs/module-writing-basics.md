# How to write a DFTimewolf Module

The purpose of this guide is to walk a contributor through the basics of how to write a DFTimewolf module. Our example will perform the following:

* Receive filepaths of files on the local filesystem
* Hash the files and check against a list of hashes
* Move matching files to an output directory
* Keep only matching files in the state for processing by a later module

## 0 - An empty template

Each module will be a subclass of either a `BaseModule` or `ThreadAwareModule`. The latter supports running multiple actions in parallel, and so you should use a `ThreadAwareModule` when you will be processing multiple inputs that don't interact. For example, you may perform the same operation on multiple files in your local filesystem, or multiple disk snapshots in a cloud computing environment. Alternatively, you should use a `BaseModule` if you intend to only operate on a single entity, or if a system you interact with can handle its own parallel processing.

A third type of module available is the `PreflightModule`. While functionaly identical to `BaseModule` the orchestration runs all `PreflightModule`s before standard modules. For example, you could use a `PreflightModule` to check for access to a cloud environment.

Our example will be a `ThreadAwareModule` as the methods to be implemented are a superset of those for `BaseModule`. Our empty template starts as follows:

```python
class FileHashModule(module.ThreadAwareModule):
  def __init__(self, state, name, critical):
    """Init."""
    (FileHashModule, self).__init__(state, name=name, critical=critical)

  def GetThreadOnContainerType(self):
    """What container type to thread on."""

  def KeepThreadedContainersInState(self) -> bool:
      """Keep, or pop the containers used for threading."""

  def GetThreadPoolSize(self):
    """Thread Pool Size."""

  def SetUp(self):
    """SetUp."""

  def PreProcess(self):
    """PreProcess."""

  def Process(self, container):
    """Processing."""

  def PostProcess(self):
    """PostProcessing."""


modules_manager.ModulesManager.RegisterModule(FileHashModule)
```

In this template we have left out type checking for brevity, but if you wish to contribute your module upstream, you will need type annotations, checked by mypy, pytype and pylint.

### \_\_init__()

A standard class method, use this to declare any class members.

### GetThreadOnContainerType()

Specific to `ThreadAwareModule` this method should return a container type that will be the basis of parallel processing.

### GetThreadPoolSize()

Specific to `ThreadAwareModule` this method tells the orchestration how many parallel threads to use for this module's `Process()` method.

### KeepThreadedContainersInState()

Specific to `ThreadAwareModule` this method returns True in the base class. If set to false by the child class, containers used for parallel processing will be popped from the state.

### SetUp()

Called by the orchestration only once, with parameters as defined by the recipe file.

### PreProcess()

Specific to `ThreadAwareModule`, this method is called exactly once by the orchestration between `SetUp()` and `Process()`.

### Process()

This method performs the bulk of the processing action. This method is called for each module in parallel, based on dependencies as outlines by the recipe file.

For a `BaseModule` no parameters will be passed in, but for a `ThreadAwareModule` the method will be called with a single container of the type specified in `GetThreadOnContainerType()`

### PostProcess()

Specific to `ThreadAwareModule`, this method is called exactly once by the orchestration after `Process()`.

## 1 - Parallel Processing Helpers

Three of the methods outlined above are used to tell the orchestration how to handle parallel processing.

The `GetThreadOnContainerType()` method is used to identify which container is used for threading. That is, this is the container type that will get passed to `Process(container)` one at a time. Since we're operating on local filesystem files, we can use the existing container, `containers.File`.

```python
  def GetThreadOnContainerType(self):
    return containers.File
```

Second of these methods is `GetThreadPoolSize()` which tells the orchestration how many threads this module supports. Since we are doing local processing, we will set the number of threads to be based on the number of CPUs in the machine doing the work - halved to ensure we're not being greedy on local resources.

```python
  def GetThreadPoolSize(self):
    count = math.floor(os.cpu_count() / 2)
    return 1 if count < 1 else count
```

Finally, we want to operate on file containers, and only keep those file containers in the state if the hash is matched. We will do that by telling the orchestration to pop the containers when passed to `Process()` and add the matches back.

```python
  def KeepThreadedContainersInState(self):
    return False
```

## 2 - Initialisation

Two methods are used as part of module initialisation: The python class `__init__()` and DFTimewolf's `SetUp()` method.

\_\_init__ is simple enough, we only need to declare the class members:

```python
  def __init__(self, state, name, critical):
    super(FileRegexModule, self).__init__(state, name=name, critical=critical)
    self.hashes = []
    self.destination_dir = ''
```

`SetUp()` is called by the orchestration with parameters as defined by the recipe file. Our module is going to receive two parameters: a comma separated list of files and a comma separated list of hashes. For any module that can take input in this manner should expect comma seperated values in a string rather than a `list` because it will likely come from a human on the CLI.

```python
  def SetUp(self, paths, hashes, destination_directory):
    # Set the hashes
    self.hashes = hashes.split(',')

    # Files passed in should be added to the container store in the state.
    for p in paths.split(','):
      if p:
        filename = os.path.basename(p)
        self.StoreContainer(containers.File(name=filename, path=p))
```

## 3 - Processing

Now we arrive at the heavy lifting of our module, we have 3 methods remaining to implement.

`PreProcess` is used for any actions that aren't considered part of the `SetUp()` but also need to be taken before processing. In an example that operates on a cloud platform, you could use this to create IAM permissions needed to perform the work.

```python
  def PreProcess(self):
    if not os.access(self.destination_dir, os.W_OK):
      self.ModuleError(
          message=f'Cannot write to destination {self.destination_dir}, bailing out',
          critical=True)
```

In our contrived example, we're going to test we have write permissions on the destination directory, and if not, we are raising a module error that will be handled by the orchestration.

Next up is `Process(container)`. This method will receive one `File` container (as per `GetThreadOnContainerType()`) and perform the check.

```python
  def Process(container):
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()

    with open(container.path, 'rb') as f:
        while True:
          data = f.read(BUF_SIZE)
          if not data:
              break
          sha1.update(data)

    digest = sha1.hexdigest()
    if digest in self.hashes:
      os.rename(container.path, f'{self.destination_dir}/{container.name}')
      self.StoreContainer(
          containers.File(
              name=container.name,
              path=f'{self.destination_dir}/{container.name}'))
```

Finally, we would implement a `PostProcess()` method. In our example, there is no great need for post processing, but for the sake of the example, we might have the following:

```python
  def PostProcess():
    count = len(self.GetContainers(containers.File))
    if count == 0:
      self.ModuleError(
          message=f'No matching hashes found.',
          critical=False)
```
