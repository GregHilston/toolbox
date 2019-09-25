#!/usr/bin/env bash
set -e

# TODO take in command line args and check for the correct number or required one

gcloud spanner rows insert --instance=ad-infrastructure --database=user_data --table=AccountPos --data=AccountId=MDQyYjhlYjQtNzllZC00OGNkLThiMTMtOWRiN2Y5NmQ4Mjlj,PosId=MQ==,PosName="Grehg",PosNumber=1234