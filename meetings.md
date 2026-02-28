# Meetings notes

## Meeting 1.

- **DATE:** 2026/02/06
- **PARTICIPANTS:** Anqi Zhou, Junxuan Ling, Tianyi Liu
- **TEACHER:** Ivan Sanchez

### Minutes

The students introduced their idea about developing a recipe API.

Then the students talked about their concerns regarding the details within the database design, for example, how to handle tag-like attributes (allergies). Some of the concerns comes from the limitation of sqlite. The teacher recommended to do a tag-matching on the frontend rather then to handle it during the query stage.

It's also recommended to cut some of the tables to keep the project concise.

Lastly, the Spoonacular API presented in the deliverable 0 was discussed and several points that were not quite RESTful were spotted.

### Action points

- Improve the database design
    - Optimize the database schema by reducing the number of tables.
    - Modify the scheme design to handle the tag-matching scenario.
- Study further about the Spoonacular API and improve deliverable 0.

## Meeting 2.

- **DATE:** 2026/02/13
- **PARTICIPANTS:** Anqi Zhou, Junxuan Ling, Tianyi Liu
- **TEACHER:** Ivan Sanchez

### Minutes

- Database
    - The technology stack is introduced (SQLite, SQLAlchemy)

    - Many-to-Many Relationship is discussed, e.g. The table linking recipes and ingredients is treated as a model rather than just a helper table because it stores other data such as amounts.
    - Nullability and mandatory fields are confirmed to be implemented correctly.

- Readme: the database creation logic can be put into a python script and anyone who uses the project needs only to run the script.

- Next deliverable
    - The distinction between internal database models and external API resources is discussed.

    - The next deliverable will be assessed based on test coverage (>=85%). Tests must cover both successful requests (200 OK) and error handling.

### Action points

- Put all setup and configuration instructions in one central place or clearly linked.
- Next deliverable
    - Remember the distinction between database models and API resources.
    - Implement the API as introduced in the exercise.
    - Put effort to testing.
    - To leave time for testing, start as soon as possible.
    - Avoid adding too much extra functionality.

## Meeting 3.

- **DATE:**
- **PARTICIPANTS:**
- **TEACHER:**

### Minutes

_Summary of what was discussed during the meeting_

### Action points

_List here the actions points discussed with assistants_

## Midterm meeting

- **DATE:**
- **PARTICIPANTS:**
- **TEACHER:**

### Minutes

_Summary of what was discussed during the meeting_

### Action points

_List here the actions points discussed with assistants_

## Final meeting

- **DATE:**
- **PARTICIPANTS:**
- **TEACHER:**

### Minutes

_Summary of what was discussed during the meeting_

### Action points

_List here the actions points discussed with assistants_
