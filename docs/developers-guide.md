# Developer's guide

This page gives a few hints on how to develop new recipes and modules for
dftimewolf. Start with the [architecture](architecture.md)
page if you haven't read it already.

## Codereview
As for other Log2Timeline projects, all contributions to dfTimewolf undergo code review. The process is documented [here](https://github.com/log2timeline/l2tdocs/blob/master/process/Code%20review%20process.md). 

## Code style
dfTimewolf follows the [Log2Timeline style guide](https://github.com/log2timeline/l2tdocs/blob/master/process/Style-guide.md), using snake_case for method names, and not CamelCase.

## Creating a recipe

If you're not satisfied with the way modules are chained, or default arguments
that are passed to some of the recipes, then you can create your own. See
[existing
recipes](https://github.com/log2timeline/dftimewolf/tree/master/dftimewolf/cli/recipes)
for simple examples like
[local_plaso](https://github.com/log2timeline/dftimewolf/blob/master/dftimewolf/cli/recipes/local_plaso.py).
Details on recipe keys are given
[here](architecture.md#recipes).

### Recipe arguments

Recipes launch Modules with a given set of arguments. Arguments can be specified
in different ways:

*   Hardcoded values in the recipe's Python code
*   `@` parameters that are dynamically changed, either:
    *   Through a `~/.dftimewolfrc` file
    *   Through the command line

Parameters are declared for each Module in a recipe's `recipe` variable in the
form of `@parameter` placeholders. How these are populated is then specified in
the `args` variable right after, as a list of `(argument, help_text,
default_value)` tuples that will be passed to `argparse`. For example, the
public version of the
[grr_artifact_hosts.py](https://github.com/log2timeline/dftimewolf/blob/master/dftimewolf/cli/recipes/grr_artifact_hosts.py)
recipe specifies arguments in the following way:

    args = [
        ('hosts', 'Comma-separated list of hosts to process', None),
        ('reason', 'Reason for collection', None),
        ('--artifacts', 'Comma-separated list of artifacts to fetch '
         '(override default artifacts)', None),
        ('--extra_artifacts', 'Comma-separated list of artifacts to append '
         'to the default artifact list', None),
        ('--use_tsk', 'Use TSK to fetch artifacts', False),
        ('--approvers', 'Emails for GRR approval request', None),
        ('--sketch_id', 'Sketch to which the timeline should be added', None),
        ('--incident_id', 'Incident ID (used for Timesketch description)', None),
        ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')

    ]

`hosts` and `reason` are positional arguments - they **must** be provided
through the command line. `artifact_list`, `extra_artifacts`, `use_tsk`,
`sketch_id`, and `grr_server_url` are all optional. If they are not specified
through the command line, the default argument will be used.

## Modules

If dftimewolf lacks the actual processing logic, you need to create a new
module. If you can achieve your goal in Python, then you can include it in
dfTimewolf. "There is no learning curve™".

Check out the [Module architecture](architecture#modules)
and read up on simple existing modules such as the
[LocalPlasoProcessor](https://github.com/log2timeline/dftimewolf/blob/master/dftimewolf/lib/processors/localplaso.py)
module for an example of simple Module.
