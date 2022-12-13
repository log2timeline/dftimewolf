# Architecture

The main concepts you need to be aware of when digging into dfTimewolf's
codebase are:

- Modules
- Recipes
- The `state` object

**Modules** are individual Python objects that will interact with specific
platforms depending on attributes passed through the command line or
`AttributeContainer` objects created by a previous module's execution.
**Recipes** are instructions that define how modules are chained, essentially
defining which Module's output becomes another Module's input. Input and output
are all stored in a **State** object that is attached to each module.

## Modules

Modules all extend the `BaseModule`
[class](https://github.com/log2timeline/dftimewolf/blob/main/dftimewolf/lib/module.py),
and implement the `SetUp`, and `Process` functions.

`SetUp` is what is called with the recipe's modified arguments. Actions here
should include things that have low overhead and can be accomplished with no big
delay, like checking for API permissions, verifying that a file exists, etc. The
idea here is to detect working conditions and "fail early" if the module can't
run correctly.

`Process` is where all the magic happens - here is where you'll want to
parallelize (see also [Thread Aware Modules](#thread-aware-modules)) things as
much as possible (copying a disk, running plaso, etc.). You'll be reading from
containers pushed by previous modules (e.g. processed plaso files) and adding
your own for future modules to process. Accessing containers is done through the
`GetContainers` and `StoreContainer` functions of the `state` object.

Tip: If you want your module to be able to take inputs from both recipe
arguments or the state, consider including something like the following in your
`SetUp`:

```python
  for p in param.split(','):
    self.state.StoreContainer(containers.MyContainer(p))
```

This way, any recipe arguments (in this example, comma separated) are available
in `Process` via `self.state.GetContainers()`, in addition to any containers
from previous modules.

### Thread Aware Modules

If your module takes multiple inputs you can take advantage of the
`ThreadAwareModule` base class to have your inputs processed in parallel
threads. The following are the differences from implementing `BaseModule`:

* Process takes a single container argument. You process this single container,
rather than sourcing containers to process from `self.state.GetContainers()`.
* Required method overrides:
  * `GetThreadOnContainerType()` - The type of container that is to be used as
  input to the parallel threads.
  * `GetThreadPoolSize()` - Determine the maximum number of simultaneous threads.
* Optional method overrides:
  * `PreProcess()` & `PostProcess()` - Work that needs to be done prior to, or
  after `Process(container)`, that only occurs once regardless of the number of
  inputs.
  * `KeepThreadedContainersInState()` - Used to determine whether the containers
  passed to `Process(container)` should be removed from the state after
  processing.

### Logging

Modules can log messages to make the execution flow clearer for the user. This
is done through the module's `logger` attribute: `self.logger.info('message')`.
This uses the standard python `logging` module so can use functions like `info`,
`warning`, `debug`.

### Error reporting

Modules can also report errors using their `ModuleError` function. Errors added
this way will be reported at the end of the run. Semantically, they mean that
the recipe flow didn't go as expected and should be examined.

`ModuleError` also takes a `critical` parameter, which will raise an exception
and interrupt the flow of the whole recipe. This should be used for errors that
dftimewolf can't recover from (e.g. if a binary run by one of the modules can't
be found on disk).

## Recipes

Recipes are JSON files that describe how Modules are chained, and which
parameters can be ingested from the command-line. A recipe JSON object follows a
specific format:

- `name`: This is the name with which the recipe will be invoked (e.g.
  `plaso_ts`).
- `description`: This is a longer description of what the recipe does. It will
  show up in the help message when invoking `dftimewolf recipe_hame -h`.
- `short_description`: This is what will show up in the help message when
  invoking `dftimewolf -h`.
- `modules`: An array of JSON objects describing modules and their corresponding
  arguments.
  - `wants`: What other modules this module should wait for before calling its
    `Process` function.
  - `name`: The name of the module class that will be instantiated.
  - `runtime_name`: Optional argument, use this for recipes when you're using
    the same module more than once.
  - `args`: A list of (argument_name, argument) tuples that will be passed on to
    the module's `SetUp()` function. If `argument` starts with an `@`, it will
    be replaced with its corresponding value from the command-line or the
    `~/.dftimewolfrc` file.
- `args`: Recipes need to describe the way arguments are handled in a global
  `args` variable. This variable is a list of
  `(switch, help_message, default_value)` tuples that will be passed to the
  `argparse.add_argument` function for later parsing.

## State and AttributeContainers

The State object is an instance of the
[DFTimewolfState class](https://github.com/log2timeline/dftimewolf/blob/main/dftimewolf/lib/state.py).
It has a couple of useful functions and attributes:

- `StoreContainer`: Store your containers to make them available to future
  modules.
- `GetContainers`: Retrieve the containers stored using `StoreContainer`. It
  takes a `container_class` param where you can select which containers you're
  interested in.
- `StreamContainer`: This will push a container on the streaming queue, and any
  registered streaming callbacks will be called on the container. Containers
  stored this way are not persistent (e.g. can't be accessed with
  `GetContainers` later on).
- `RegisterStreamingCallback`: Use this to register a function that will be
  called on the container as it is streamed in real-time.

## Life of a dfTimewolf run

The dfTimewolf cycle is as follows:

- The recipe JSON is parsed, all requested modules are instantiated, as well as
  the semaphores that will schedule the execution of the Module's `Process`
  functions.
- Command-line arguments are taken into account and passed to Module's `SetUp`
  function. This occurs in parallel for all modules, regardless of the semaphores
  they declared in the recipe.
- The modules with no blocking semaphores start running their `Process`
  function. At the end of their run, they free their semaphore, signalling other
  modules that they can proceed with their own `Process` function.
- This cycle repeats until all modules have called their `Process` function.
