## Pipe of Insight
Pipe of Insight is a Django based web application with the primary purpose of helping users draft the optimal hero in their Dota 2 matches. I developed this project as part of a 3 week sprint during the Insight Data Science 19C session; documentation and tests are admittedly lacking, but hopefully this README will offer a bit of clarity about the organizational structure of the project.

---

### Project structrue
The project structure follows the standard Django project structure. From the top level directory, the main application code is stored in the directory `dota_chat`. The following gives a brief summary of the most relevant files/directories:

*  `management/commands/` &mdash; this directory contains a number of scripts primarily used to gather, clean, and restructure various data and populate the database.
* `views.py` and `view_utils.py` &mdash; these files contain the code used to pull relevant (contextual) information from the database for use in populating the template (e.g., on a hero detail page). There are also functions used generate various visualizations (e.g., hero popularity plots, match up stats, etc).
* `model_test_set.py` &mdash; this file contains the code used to generate/train the classifiers used for the drafting predictions. This was developed alongside (but separate from) the application framework. The training/validation/testing is included in this file. This code is mostly run standalone, but as the project develops this will eventually need to be fully integrated into the project framework.
* `models.py` &mdash; this file contains the Django models used to define the database schema. In other words, this is where the mapping between Heros, Abilities, Matches, Players, Users, etc. is defined.
* `tables.py` and `forms.py` &mdash; these files contain some class definitions for displaying data in the template.
* `templates/dota_chat` &mdash; this directory contains the HTML, JavaScript, and Django templating used to generate the various pages of the application.



