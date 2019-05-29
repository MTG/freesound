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

## Specific notes

### Custom Django permissions

If there is a need for defining custom permissions we should define them in the corresponding model's `Meta` class
as [described in the Django docs](https://docs.djangoproject.com/en/dev/topics/auth/customizing/#custom-permissions). There
is no generic model to **host** all custom permissions, but we'll add them to the most closely related model. These
permissions should then be added to a `Group` so that we can manage them properly in the Django admin. The `Group` should
be created in the corresponding database migration in which the permission is added to the model.

Currently, we only use the following custom permissions:
* `tickets.can_moderate` (in `Ticket` model, used to allow sound moderation)
* `forum.can_moderate_forum` (in `Post` model, used to allowforum moderation)
* `sounds.can_describe_in_bulk` (in `BulkUploadProgress` model, used to allow bulk upload for users who don't meet the other common requirements)
