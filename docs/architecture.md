# Architecture

## Three main objects

The main concepts you need to be aware of when digging into dfTimewolf's
codebase are:

*   Modules
*   Recipes
*   The `state` attribute

**Modules** are individual Python objects that will (for the most part) take
some kind of input and produce some kind of output. **Recipes** are instructions
that define how modules are chained, essentially defining which Module's output
becomes another Module's input. Input and output are all stored in a **State**
object that is attached to each module.

### Modules

Modules all extend the `BaseModule`
[class](https://github.com/log2timeline/dftimewolf/blob/master/dftimewolf/lib/module.py),
and implement the `setup`, `process` and `CleanUp` methods.

`setup` is what is called with the recipe's modified arguments. Actions here
should include things that have low overhead and can be accomplished
sequentially with no big delay, like checking for permissions on a cloud
project, creating an analysis VM, verifying that a file exists, etc.

`process` is where all the magic happens - here is where you'll want to
parallelize things as much as possible (copying a disk, running plaso, etc.).
You'll be adding information to the state (e.g. processed plaso files) in the
module's output as you go. You can access a previous module's output (i.e. your
input) using `self.state.input` and manipulate the current module's output using
`self.state.output`.

`CleanUp` is mostly optional, in case you manipulated the state in a way that
needs post-processing (e.g. adding a "# out of #" description to the module's
output)

### Recipes

Recipes are a Python dictionary that describe how Modules are chained, and which
parameters can be ingested from the command-line. These dictionaries have a few
specific keys:

*   `name`: This is the name with which the recipe will be invoked (e.g.
    `local_plaso`)
*   `short_description`: This is what will show up in the help message when
    invoking `dftimewolf -h`
*   `modules`: A list of dicts describing modules and their corresponding
    arguments.
    *   `name`: The name of the module class that will be instantiated
    *   `args`: A list of (argument_name, argument) tuples that will be passed
        on to the module's `SetUp()` method. If `argument` starts with an `@`,
        it will be replaced with its corresponding value from the command-line
        or the `~/.dftimewolfrc` file.

Recipes need to describe the way arguments are handled in a global `args`
variable. This variable is a list of `(switch, help_message, default_value)`
tuples that will be passed to the `argparse.add_argument` method for later
parsing.

### State

The State object is an instance of the [DFTimewolfState
class](https://github.com/log2timeline/dftimewolf/blob/master/dftimewolf/lib/state.py).
It has a couple of useful methods:

*   `add_error`: Used by modules to indicate that an error occurred during
    execution (e.g. missing file, unauthorized access).
*   `check_errors`: Display any errors that have been added. If any critical
    errors were added, dftimewolf will stop the execution of the recipe and
    exit. Non-critical errors will just be displayed and execution will
    continue.
*   `CleanUp`: Resets the state: moves the output data to the input attribute
    and clears the output for the next Module. Moves remaining (and therefore
    non-critical) errors to global_errors for later processing.

## What happens when you run a recipe

The dftimewolf cycle is as follows:

*   The recipe is parsed, and the first Module is instantiated
*   Command-line arguments are taken into account and passed to Module's `setup`
    method.
    *   Errors are checked
*   The module's `process` method is called
    *   Errors are checked
*   Cleanup occurs; the output becomes input and the process is repeated with
    the next module in the recipe.
