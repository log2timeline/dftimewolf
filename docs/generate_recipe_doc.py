"""
Helper script to autogenerate documentation for recipes.
"""

import os
import sys
import json
import graphviz

from dftimewolf.lib import resources

# These are the first strings that will be generated in the file.
HEADER = """
# Recipe list

This is an auto-generated list of dfTimewolf recipes.

To regenerate this list, from the repository root, run:

```
poetry install -d
python docs/generate_recipe_doc.py data/recipes
```

---
"""

# This is the template for representing a recipe's documentation
#
# ## <RECIPE_NAME
#
# <SHORT_DESCRIPTION>
#
# **Details:**
#
# <LONG_DESCRIPTION>
#
# CLI parameters:
#
# <CLI PARAMS>
#
# Modules: <LIST OF MODULES USED BY THE RECIPE>
#
# **Module graph**
#
# <PNG TO A GRAPH SHOWING THE SEQUENCE OF MODULES>
RECIPE_FORMAT_TEMPLATE = """## `{0:s}`

{1:s}

**Details:**

{2:s}

**CLI parameters:**

{3:s}

Modules: {4:s}

**Module graph**

![{0:s}](_static/graphviz/{0:s}.png)

----

"""


def load_recipes_from_dir(directory):
  """Loads all recipe JSON files from a given directory."""
  recipes = []
  for root, _, files in os.walk(directory):
    for file in files:
      if file.endswith(".json"):
        with open(os.path.join(root, file)) as jsonf:
          recipe_json = json.load(jsonf)
          # Skip JSON files that are likely not recipes.
          if 'name' in recipe_json and 'modules' in recipe_json:
            recipes.append(recipe_json)
  return recipes


def generate_args_description(recipe):
  """Generates a description of the CLI arguments for a given recipe."""
  args = recipe['args']
  formatted_string = 'Parameter|Default value|Description\n'
  formatted_string += '---------|-------------|-----------\n'
  for arg in args:
    recipe_args = resources.RecipeArgs(*arg)
    formatted_string += (f'`{recipe_args.switch}`|'
                         f'`{repr(recipe_args.default)}`|'
                         f'{recipe_args.help_text}\n')
  return formatted_string + '\n\n'


def recipe_to_doc(recipe, destination_directory=''):
  """Updates recipe-list.md with the markdown and graph for a given recipe."""
  recipe_name = recipe['name']
  module_names = [m.get('runtime_name', m['name']) for m in recipe['modules']]
  mkd = RECIPE_FORMAT_TEMPLATE.format(
      recipe['name'], str(recipe['short_description']),
      str(recipe['description']),
      generate_args_description(recipe),
      ', '.join([f'`{name}`' for name in module_names]))

  with open(f'{destination_directory}/recipe-list.md', 'a') as f:
    f.write(mkd)

  graph = generate_graph(recipe)
  graph.render(
      f'{destination_directory}/_static/graphviz/{recipe_name}', cleanup=True)


def generate_graph(recipe):
  """Generates a Graphviz graph for a given recipe."""
  dot = graphviz.Digraph('G', comment='dfTimewolf module graph', format='png')
  dot.attr(compound='true')
  dot.attr(center='true')
  dot.attr(nodesep='0.5')
  dot.attr(fontname='Sans')

  if recipe.get('preflights'):
    with dot.subgraph(name='cluster_preflights') as p_cluster:
      p_cluster.attr(color='lightblue')
      p_cluster.attr(label='Preflights', fontcolor='lightgrey')
      p_cluster.node_attr.update(style='filled', color='lightgrey')
      for module in recipe['preflights']:
        modname = module.get('runtime_name', module['name'])
        p_cluster.node(modname, shape='box', fontname='Sans')
        for wants in module['wants']:
          p_cluster.edge(wants, modname)

  with dot.subgraph(name='cluster_modules') as m_cluster:
    m_cluster.attr(color='lightgrey')
    m_cluster.attr(label='Modules', fontcolor='lightgrey')
    m_cluster.attr(fontname='Sans')
    for module in recipe['modules']:
      modname = module.get('runtime_name', module['name'])
      m_cluster.node(modname, shape='box', fontname='Sans')
      for wants in module['wants']:
        m_cluster.edge(wants, modname)

  if recipe.get('preflights'):
    first_module = recipe['preflights'][0]
    cluster = 'cluster_preflights'
  else:
    first_module = recipe['modules'][0]
    cluster = 'cluster_modules'

  if cluster == 'cluster_preflights':
    first_actual_module = recipe['modules'][0]
    first_module_name = first_module.get('runtime_name', first_module['name'])
    first_actual_module_name = first_actual_module.get(
        'runtime_name', first_actual_module['name'])
    dot.edge(
        first_module_name,
        first_actual_module_name,
        ltail='cluster_preflights',
        lhead='cluster_modules')

  return dot


if __name__ == '__main__':
  recipedir = os.path.abspath(sys.argv[1])
  outputdir = os.path.abspath(sys.argv[2])
  if not os.path.exists(recipedir):
    print(f'Recipe directory does not exist: {recipedir}')
    sys.exit(1)
  print(f'Generating docs for recipes in {recipedir}')

  # Write a static header to the recipe-list.md file.
  with open(f'{outputdir}/recipe-list.md', 'w') as f:
    f.write(HEADER)

  recipes = load_recipes_from_dir(recipedir)
  recipes.sort(key=lambda r: r['name'])
  for recipe in recipes:
    print(f'Generating docs for {recipe["name"]}')
    recipe_to_doc(recipe, outputdir)
