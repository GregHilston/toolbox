WKSP=$(get_workspace.sh)
EMPT=$(workspace_empty.sh $WKSP)

# This part exits the script if the workspace isn't empty
# This could be put conditionally in the CASE statements
if [ $EMPT -ne 1 ] ; then
	exit 0
fi



case $WKSP in
	

	SLACK) exec google-chrome --new-window "https://app.slack.com/client/T04700HRA/GTZF4586B" ;;
	#MCHAT) exec google-chrome --new-window "https://chat.madwire.net/channel/Madwire" ;;
	ZOOM) exec zoom ;;
	MAIL) exec google-chrome --new-window "https://mail.google.com/mail/u/0/#inbox" ;;
	JIRA) exec google-chrome --new-window "https://madsoftware.atlassian.net/secure/RapidBoard.jspa?rapidView=8" ;;

	NPP) exec notepadqq ;;
	MSQL) exec mysql-workbench ;;
	POST) exec Postman ;;
	CAPT) exec Captain ;;
	MONG) exec robo3t ;;

	PHP1) exec phpstorm.sh ~/.captain/headproxy/order-collector ;;
	PHP2) exec phpstorm.sh ~/.captain/headproxy/crm2 ;;
	PHP3) exec phpstorm.sh ~/.captain/headproxy/crm-api ;;
	PHP4) exec phpstorm.sh ~/.captain/headproxy/mm360v2front ;;
	PHP5) exec phpstorm.sh ~/.captain/headproxy/crm2-integration-tests ;;
	PHP6) exec psmad madscripts ;;
	
	CH*)
		CHNUM=${WKSP//[!0-9]/}
		if [ $CHNUM -ge 10 ] ; then
			exec google-chrome --new-window --incognito
		else
			exec google-chrome --new-window
		fi
	;;

	F*)
		exec nautilus 
	;;

	T*)
		exec xterm 
	;;


esac
