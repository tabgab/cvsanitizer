Project description.

1 Privacy Guard - Python Utility.

Input: CV in PDF format.
Output: CV in JSON format with PII removed, and a JSON file with the mapping of the PII to the original text.

This utility is used to remove personally identifiable information (PII) from CVs.
The file formati is PDF, which needs to be parsed and then the text needs to be searched for PII.
PII is defined as any information that can be used to identify a person, such as name, address, phone number, email address, social security number, driver's license number, passport number, etc.
Do not use AI for this sweep, prepare a logical algorithm to identify it and mark it in the document.

As a starting point, you can look at the privacy_guard.py file, which implements a similar functionality.
It needs to be improved, and also needs to be prepared for localization. There are many pitfalls with this approach, but we cannot use AI for this sweep as the whole point is to remove PII from CVs before sending them to LLMs. International characters, typos, capitalization, etc. need to be taken into account.

The next step after identifying the PII is to remove it from the document, replacing it with a tag "<pii>" and a type and serial number (e.g. <pii type="email" serial="1">). Store this in a separate file, with the same name as the CV, create a json file, with the same name as the CV, but with a .pii.json extension. This file should contain the mapping of the PII to the original text.

Map the CV without the PII to a new json file, adding _redacted to its name (e.g. cv_redacted.json).

Look at the models.py file for the database schema to understand the structure of the data and the kind of json file that needs to be created.

This needs to be an interactive utility that allows the user to preview the CV before redacting it. It should show what PII was found and mark it clearly on screen to show that the it has been marked for redaction. The user should confirm the redaction before the utility proceeds to the next step. The user can remove sections, maybe they were marked in error, or they can add sections, maybe they were not marked. When the user is satisfied, the utility should proceed to the next step. The user must confirm that the redaction is correct before the utility proceeds to the next step. The confirmation of the user has to be marked and stored in the database, marking the time, date and username of the user. Then the software should proceed with the redaction, creating the .json files described above. One .json file, structured according to the models.py file, and one .pii.json file, containing the mapping of the PII to the original text so that the PII can be restored later. 

You can use the CV_Gabor_Tabi.pdf file as an example to test the utility.

Use a github repo for the code, regularly push your code to https://github.com/tabgab/cvsanitizer.git online with meaningful comments. Once complete, test the code. Create a readme with detailed instructions on how the utility can be called from another program. Ensure that it works both from a python and an npm environment, and could be hosted on AWS.