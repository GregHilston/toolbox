#!/usr/bin/env bash
set -e

# TODO take in command line args and check for the correct number or required one

gcloud spanner rows insert --instance=ad-infrastructure --database=user_data --table=CustomerPurchases --data=AccountId=MDQyYjhlYjQtNzllZC00OGNkLThiMTMtOWRiN2Y5NmQ4Mjlj,CustomerId=MDY0MzU2ZjEtMWMxYS00Zjg2LTg5MWEtYTVhMGMzYTAzN2I1,PosId=MQ==,CustomerCrmNumber=123,CustomerPosNumber=456