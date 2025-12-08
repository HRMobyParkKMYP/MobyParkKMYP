## - function
## ~ description
## > returns/gives back
## = found issues

- load_json(filename : unknown):
~ loads a json file into a python readable data structures
> loaded file or on FileNotFound an empty List
!=

- write_json(filename: unknown, data : unknown):
~ overwrites selected data over the current data in the json file
> void
!= 

- load_csv(filename : unknown):
~ loads a csv into a list row for row
> loaded list or on FileNotFound an empty list
!=

- write_csv(filename : unknown, data : unknown):
~ overwrites current data in csv by new data
> void
!=

- load_text(filename : unknown):
~ loads text data into a list
> list with lines from text or on FileNotFound an empty list
!=

- write_text(filename : unknown, data : unknown):
~ overrides current data in file by new data seperated by newline
> void
!=

- save_data(filename : unknown, data : unknown):
~ datawriter handler by checking if file format matches created datawriter helper functions
> void or on ValueError a string
!=

- load_data(filename : unknown):
~ dataloader handler by checking if the file format string matches created datareader helper functions
> void
!= does not have error handling like (func)save_data(-)

- last 10 functions negligable to document, see Main Findings

# Used libraries/imports
- json
- csv

# Main Findings:
- No type hinting
- data readers load full files, bad for performance
- data writer functions override full file with set data. big chance for dataloss. bad performance
- neglected error handling
- 10 unnecesary wrapper functions calling load and save data with set string parameters (and data)

# Reccomendations 
- make the strings constants and removing the wrapper functions