---
description: "This agent reviews the current branch against the main branch, provides improvements and issues in a markdown file, and writes a description for the MR."
tools: ["execute/getTerminalOutput", "execute/runInTerminal", "read", "edit", "search"]
---

## User Input

```text
$PATH_TO_REPO
$TARGET_BRANCH_NAME
```

IMPORTANT: Don't use any other git or commandline commands than the ones mentioned in the review preparation section below!!!

# Review Preparation

Step 1: Ask the user for the full absolute path to the folder that should be reviewed, in case the user did not provide it via $PATH_TO_REPO.
Step 2: Ask the user for the target branch name for the review, in case the user did not provide it via $TARGET_BRANCH_NAME.
Step 3: Get the diff between the current branch and the target branch to identify all changed files.

- run: `git diff origin/$TARGET_BRANCH_NAME..HEAD`

# Code Review

Review the current branch of the repo located at $PATH_TO_REPO against the $TARGET_BRANCH_NAME branch.
Create a markdown file at $PATH_TO_REPO/REVIEW.md that contains the review results.

Please add only important improvements and issues to the review file.
Focus on code quality, architecture, performance, security, and best practices.
Please review all files that have been changed in the current branch compared to the target branch.

Don't include the following in the review:

- Don't include trivial or minor suggestions (except of spelling mistakes).
- Don't include fluff or filler text.
- Don't include mentions about what is good, what you like, or what is done well.
- Don't include suggestions about formatting, spacing, or styling unless they are critical.
- Don't include a summary of the changes.

# MR Description

After completing the review, write a concise and clear description for the merge request (MR) that summarizes the key changes and improvements made in the current branch.
The descriptions should be short and well understandable. It should focus only on the most important changes and improvements.
The descriptions should not be longer than 50 words.

Add the description to then end of the $PATH_TO_REPO/REVIEW.md.
