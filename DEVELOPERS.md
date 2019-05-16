# Freesound Developer notes

## Code layout
Where possible, use consistent formatting for file layout. In pycharm take advantage of the 
`Code`→`Optimize imports` and `Code`→`Reformat code` menu items in order to have a consistent 
code layout.

## Code documentation
We use Google-style docstrings.
You can see examples of these docstrings here: 
https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html

In pycharm you can set this format by choosing in Preferences `Tools`→`Python Integrated Tools` 
and change the Docstring format.

Make sure whenever possible you add type annotations to the variables, e.g.

    Args:
        param1 (int): The first parameter.

Always use a . to end sentences of a docstring. This includes argument lists 
and other lists (see the Google example linked above)

## Making changes
Prefer to create a pull request for all changes. This allows us to keep a record of the changes 
that were made, and allow feedback if necessary


Deployment process:
When PRs are merged, add the [merged] label to the ticket that it solves. This allows us to make a list of 
changes for release notes or other documentation. Once the release has been made, remove these labels from 
these tickets.