#!/bin/bash

# For more details see [1]
#
# [1] https://docs.microsoft.com/en-us/azure/app-service/scripts/app-service-cli-deploy-staging-environment

RGROUP_NAME=LocanoAppGroup
WEBAPP_NAME=locano

GIT_REPO=git@github.com:anton-nayshtut/locanobot.git

STAGING_SLOT_NAME=staging

webapp_info() {
    az webapp show --name $WEBAPP_NAME --resource-group $RGROUP_NAME || return 1

    return 0
}

browse() {
SLOT_NAME=$1
    SLOT_OPT=
    if [ ! -z $SLOT_NAME ]; then
        SLOT_OPT="--slot $SLOT_NAME"
    fi
    # Browse wepapp slot
    az webapp browse --name $WEBAPP_NAME \
    --resource-group $RGROUP_NAME $SLOT_OPT || return 1

    return 0
}

sel_deployment() {
SLOT_NAME=$1
GIT_BRANCH=$2
    # Deploy $GIT_BRANCH code to $SLOT_NAME slot from $GIT_REPO
    az webapp deployment source config --name $WEBAPP_NAME \
    --resource-group $RGROUP_NAME --slot $SLOT_NAME \
    --repo-url $GIT_REPO --branch $GIT_BRANCH --manual-integration || return 2

    return 0
}


create_slot() {
SLOT_NAME=$1

    #Create a deployment slot with the name $SLOT_NAME
    az webapp deployment slot create --name $WEBAPP_NAME \
    --resource-group $RGROUP_NAME --slot $SLOT_NAME || return 1

    return 0
}

swap_slot() {
SLOT_NAME=$1
    # Swap the verified/warmed up staging slot into production.
    az webapp deployment slot swap --name $WEBAPP_NAME \
    --resource-group $RGROUP_NAME --slot $SLOT_NAME || return 1

    return 0
}

delete_slot() {
SLOT_NAME=$1
    # Delete a deployment slot.
    az webapp deployment slot delete --name $WEBAPP_NAME \
    --resource-group $RGROUP_NAME --slot $SLOT_NAME || return 1

    return 0
}

list_slots() {
    az webapp deployment slot list --name $WEBAPP_NAME \
    --resource-group $RGROUP_NAME || return 1

    return 0
}

slot_host_name() {
SLOT_NAME=$1
    if [ -z $SLOT_NAME ]; then
        webapp_info |  jq ".hostNames[0]" | sed "s/\"//g"
    else
        list_slots | jq ".[] | select(.name == \"$SLOT_NAME\") | .hostNames[0]" | sed "s/\"//g"
    fi
}


is_slot_up() {
SLOT_NAME=$1
    SLOT_HOST=$(slot_host_name $SLOT_NAME)
    if [ -z SLOT_HOST ]; then
        return 1
    fi
    echo Checking http://$SLOT_HOST/...
    if curl -s --head  --request GET http://$SLOT_HOST/ | grep "200 OK" > /dev/null; then
        echo It\'s Up
        return 2
    else
        echo It\'s Down
        return 0
    fi
}


SCRIPT_NAME=$(basename $0)

usage() {
    echo "$SCRIPT_NAME - Azure $WEBAPP_NAME webapp deployment script"
    echo ""
    echo "Usage:"
    echo "    $SCRIPT_NAME [options] action"
    echo ""
    echo "Where:"
    echo "    actions:"
    echo "        help - show this help"
    echo "        ls_slots - list all slots"
    echo "        add_slot - deploy webapp to a separate slot"
    echo "        del_slot - remove deployment slot"
    echo "        config_slot - conigure deployment slot"
    echo "        swap_slot - swap the slot into production"
    echo "        browse - open the slot/webapp in browser (webapp if no slot provided)"
    echo "        is_slot_up - check whether the slot/webapp is up (webapp if no slot provided)"
    echo ""
    echo "    options:"
    echo "        -b <git_branch>"
    echo "        --branch <git_branch> - git branch to deploy"
    echo "        -s <slot_name>"
    echo "        --slot <slot_name> - deployment slot name"
    return 0
}

while [ "$1" != "" ]; do
        case $1 in
        -h|--help)
                ;;
        -b|--branch)
                shift
                GIT_BRANCH=$1
                ;;
        -s|--slot)
                shift
                SLOT_NAME=$1
                ;;
        *)
                if [ $# -ne 1 ]; then
                        echo "ERROR: unknown parameter \"$1\""
                        usage
                        exit 1
                else
                        ACTION=$1
                fi
            ;;
        esac
        shift
done


case $ACTION in
        help)
                usage
                ;;
        ls_slots)
                list_slots $
                ;;
        add_slot)
                test -z $SLOT_NAME && { echo "ERROR: slot name is mandatory" && usage && exit 1; }
                create_slot $SLOT_NAME
                ;;
        del_slot)
                test -z $SLOT_NAME && { echo "ERROR: slot name is mandatory" && usage && exit 1; }
                delete_slot $SLOT_NAME
                ;;
        config_slot)
                test -z $SLOT_NAME && { echo "ERROR: slot name is mandatory" && usage && exit 1; }
                test -z $GIT_BRANCH && { echo "ERROR: git branch is mandatory" && usage && exit 1; }
                sel_deployment $SLOT_NAME $GIT_BRANCH
                ;;
        swap_slot)
                test -z $SLOT_NAME && { echo "ERROR: slot name is mandatory" && usage && exit 1; }
                swap_slot $SLOT_NAME
                ;;
        browse)
                browse $SLOT_NAME
                ;;
        is_slot_up)
                is_slot_up $SLOT_NAME
                ;;
        *)
                echo "ERROR: unknown action \"$ACTION\""
                usage
                ;;
esac
