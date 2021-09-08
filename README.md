# GitHubAPI-Crawler
This is a fork of @user2589/ghd

## To execute the script
Create token.txt file, and list your GitHub Token per line

main.py contains a few examples

## How to create GitHub Tokens
Once you log into your GitHub account, click on your avatar - Settings - Developer settings - Personal access tokens - Generate new token - Generate token (green button at the bottom of the screen). Important: DO NOT CHECK ANY OF THE BOXES THAT DEFINE SCOPES

You could have multiple email accounts (--> multiple GitHub accounts) --> make a token for each. 

## How to contribute
Create a fork, make changes in your fork, and once finish the implementation, submit a PR.

## Changed File Analysis
The crawler API is used to fetch all the active forks of a project. Then all the forks are cloned to obtain git log files. All the forks' git log files are parsed and the changed files (modified, added, deleted) are summarized. At the end, the result (in total how much a file is changed) is outputted into an excel file, in descending order, along with fork names and commits that changed the file. 

