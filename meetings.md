# Meetings minutes

## Meeting 1.

- **DATE:** 2026/02/06
- **PARTICIPANTS:** Anqi Zhou, Junxuan Ling, Tianyi Liu
- **TEACHER:** Ivan Sanchez

### Action points

- Improve the database design
    - Optimize the database schema by reducing the number of tables.
    - Modify the scheme design to handle the tag-matching scenario.
- Study further about the Spoonacular API and improve deliverable 0.

### Notes

The students introduced their idea about developing a recipe API.

Then the students talked about their concerns regarding the details within the database design, for example, how to handle tag-like attributes (allergies). Some of the concerns comes from the limitation of sqlite. The teacher recommended to do a tag-matching on the frontend rather then to handle it during the query stage.

It's also recommended to cut some of the tables to keep the project concise.

Lastly, the Spoonacular API presented in the deliverable 0 was discussed and several points that were not quite RESTful were spotted.

## Meeting 2.

- **DATE:** 2026/02/13
- **PARTICIPANTS:** Anqi Zhou, Junxuan Ling, Tianyi Liu
- **TEACHER:** Ivan Sanchez

### Action points

- Put all setup and configuration instructions in one central place or clearly linked.
- Next deliverable
    - Remember the distinction between database models and API resources.
    - Implement the API as introduced in the exercise.
    - Put effort to testing.
    - To leave time for testing, start as soon as possible.
    - Avoid adding too much extra functionality.

### Notes

- Database
    - The technology stack is introduced (SQLite, SQLAlchemy)

    - Many-to-Many Relationship is discussed, e.g. The table linking recipes and ingredients is treated as a model rather than just a helper table because it stores other data such as amounts.
    - Nullability and mandatory fields are confirmed to be implemented correctly.

- Readme: the database creation logic can be put into a python script and anyone who uses the project needs only to run the script.

- Next deliverable
    - The distinction between internal database models and external API resources is discussed.

    - The next deliverable will be assessed based on test coverage (>=85%). Tests must cover both successful requests (200 OK) and error handling.

## Meeting 3.

- **DATE:** 2026/03/10
- **PARTICIPANTS:** Anqi Zhou, Junxuan Ling, Tianyi Liu
- **TEACHER:** Ivan Sanchez

### Action points

- Move the Swagger/API documentation implementation to the scope of Deliverable 4, as it belongs to the next phase.
- Ensure "connectedness" is properly implemented for Deliverable 4.
- Check the remaining uncovered lines in the test coverage (e.g., 400 bad request errors), though it was noted Flask handles some unsupported media types automatically.

### Notes

- HTTP Methods: The distinction between PUT and PATCH was clarified. PUT must be used when sending the complete resource representation, whereas PATCH should be used for partial modifications (e.g., updating only allergy information).

- Connectedness / HATEOAS: While full HATEOAS is not strictly required, resource connectedness is expected for the next deliverable. Responses should allow the client to navigate to related resources via links.

- Authentication: The API key authentication implemented via decorators was reviewed and approved. It correctly validates permissions rather than depending strictly on the user sending the request.

- Testing & AI Usage: Using AI (like Gemini) to generate tests is encouraged and considered a perfect use case, provided the tests are verified through linters, high coverage (currently verified at >94%), and manual review.

- Linting: The team is using flake8 instead of pylint. The teacher noted it is less strict but acceptable.

- Caching: The caching strategy was reviewed. Caching recipes and recipe collections makes sense because they are not modified frequently. Attribute searching (like limit/offset) does not need to be cached or fully implemented due to the already wide scope of the project.

## Midterm meeting

- **DATE:**
- **PARTICIPANTS:**
- **TEACHER:**

### Action points

- Deployment details such as port forwarding etc. should be put in to documents.

- Remove the 500 Internal Server Error status code from the Swagger documentation, as it represents an uncontrolled server error and should never be exposed as an expected API response.

- Implement full connectedness in the API responses by returning the full URL to related resources (e.g., the recipe URL) instead of just the resource ID. This ensures the client does not break if the server's URL architecture changes in the future.

- Ensure that for PUT requests, the entire request representation (including all user data) is sent by the client, rather than just partial data.

- Prepare for the final one-hour meeting in May. This meeting will cover a demo of the client, an external or additional service, and a review of updates made to previous deliverables.

- Complete the final reflection and evaluation deliverable individually; this specific section is not group work.

### Notes

- The teacher advised against deploying on Windows and suggested using Linux with a process control system like Supervisor. However, the current Docker implementation utilizing health checks and automatic restarts is functional.

- The Swagger API documentation is properly organized as a single file within the static main folder.

- When returning a Location header after successfully creating a resource, it is not necessary to return additional resource details in the response body, as the client can simply issue a GET request to the provided URL.


## Final meeting

- **DATE:**
- **PARTICIPANTS:**
- **TEACHER:**

### Action points

_List here the actions points discussed with assistants_

### Notes

Add here notes that you consider important. This is not mandatory
