## - function
## ~ description
## > returns/gives back
## = found issues

- calculate_price(parkinglot : Dict[unkown], sid : unknown, data : Dict[Unknown]):
~ calculates price for the time a car is parked
> tuple of; price, hours parked, diffirence of days if more then 24 hours parked
= sid is an unused parameter

- generate_payment_hash(sid : unknown, data : Dict[unknown]):
~ generates a payment hash based on sessionid and licenseplate, encoded by utf8
> hashed string
!=

- generate_transaction_validation_hash():
~ generates a random universal unique identifier (uuid) cast to string
> stringified uuid
!=

- check_payment_amount(hash : unknown):
~ checks how much has been payed
> total of payed money
?= possible logical error because of possible random hashes. not sure how it handles that

# Used libraries/imports
- datetime
- from storage_utils: load_payment_data
- from hashlib: md5
- math
- uuid

# Main Findings:
- No type hinting
- Possible logic issues
- Unused parameter
