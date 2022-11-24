#!/usr/bin/env python3

import os
import sys
import argparse

libPath = os.path.join('/home', 'streak', 'Documents', 'SignalCliApi')
sys.path.append(libPath)

from signalCli import SignalCli
from signalAccount import Account

global VERSION
VERSION: str = "0.1"

def main(args, signal:SignalCli):
    account = signal.accounts.getByNumber(args.account)
    print("Group list:")
    for group in account.groups:
        print("ID: ", group.id, "NAME: ",group.name)
    
    if (args.group != None):
        commandGroup = account.groups.getById(args.group)
    else:
        commandGroup = account.groups.getByName("Command & Control")

    if (commandGroup == None):
        # TODO: Create command group:
        signal.stopSignal()
        print("FATAL: Couldn't find command and control group.")
        exit(3)
    account.messages.sendMessage(recipients=commandGroup, body="Chatbot v%s started." % VERSION)

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="My chat bot.")
    parser.add_argument("--account", help="--account NUMBER, account number to use.")
    parser.add_argument("--group", help="--group GROUP_ID, Command and control group ID.")
    args = parser.parse_args()

    accountNumber: str
    if (args.account != None):
        accountNumber = args.account
    else:
        accountNumber = '+16134548055'
    commandGroupId: str

    try:
        signal = SignalCli()
    except Exception as e:
        print(str(e.args))
        print("Failed to start signal.")
        exit(2)
    
    main(args, signal)
    signal.stopSignal()
    