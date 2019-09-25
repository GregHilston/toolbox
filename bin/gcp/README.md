Run this query

Run 

SELECT *
FROM Customer

and pick an accountid and customerid

EX:
AccountId 	CustomerId 	ContactId 	FirstName 	LastName 
MDQyYjhlYjQtNzllZC00OGNkLThiMTMtOWRiN2Y5NmQ4Mjlj 	MDY0MzU2ZjEtMWMxYS00Zjg2LTg5MWEtYTVhMGMzYTAzN2I1 	29 	Natalie 	Sutherland 

SELECT *
FROM Customer
WHERE AccountId=b'00110a19-d48b-4e8c-96a2-628e531a9900'

to figure out which AccountId, CustomerId, PosId, CustomerCRMNumber, CustomerPosNumber to insert so it actually can join