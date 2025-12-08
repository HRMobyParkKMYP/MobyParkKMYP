## - function
## ~ description
## > returns/gives back
## = found issues

- add_session(token : unknown, user : unknown):
~ sets a user to a session token
> void
!=

- remove_session(token : unknown):
~ removes a session token key value pair
> if found None else KeyError
!=

- get_session(token : unknown):
~ gets a session token key value pair
> if found keyvalue pair else None
!=

# Used libraries/imports
- None

# Main Findings:
- No type hinting