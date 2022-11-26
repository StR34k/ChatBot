#!/usr/bin/env python3

from typing import Optional
import os
import sys
import argparse
import json

libPath = os.path.join('/home', 'streak', 'Documents', 'SignalCliApi')
sys.path.append(libPath)

from signalCli import SignalCli
from signalAttachment import Attachment
from signalAccount import Account
from signalGroup import Group
from signalReceivedMessage import ReceivedMessage

global VERSION
VERSION: str = "0.1"


global QUIT
QUIT:bool = False

global THUMBS_UP
THUMBS_UP: str = '👍'

global THUMBS_DOWN
THUMBS_DOWN: str = '👎'

def stripWhiteSpace(string:str) -> str:
    string = string.replace(' ', '')
    string = string.replace('\n', '')
    string = string.replace('\t', '')
    string = string.replace('\r', '')
    return string


def listContacts(account:Account, commandGroup:Group) -> None:
    for i in range(len(account.contacts)):
        contactBody = "ContactId: %i\n" % i
        contactBody = contactBody + 'Name: %s\n' % account.contacts[i].name
        contactBody = contactBody + 'Id: %s\n' % account.contacts[i].getId()
        account.messages.sendMessage(recipients=commandGroup, body=contactBody)
    return

def contactDetail(account:Account, commandGroup:Group, contactIndex:int) -> None:
    contact = account.contacts[contactIndex]
    detailBody = "Name: %s\n" % contact.name
    detailBody = detailBody + "Number: %s\n" % str(contact.number)
    detailBody = detailBody + "UUID: %s\n" % str(contact.uuid)
    if (contact.profile != None):
        detailBody = detailBody + "Profile: \n"
        detailBody = detailBody + "    Given Name: %s\n" % contact.profile.givenName
        detailBody = detailBody + "    Family Name: %s\n" % contact.profile.familyName
        detailBody = detailBody + "    Emoji: %s\n" % contact.profile.emoji
        detailBody = detailBody + "    About: %s\n" % contact.profile.about
        if (contact.profile.coinAddress == None or contact.profile.coinAddress == ''):
            coinAddress = "None"
        else:
            coinAddress = contact.profile.coinAddress[:8] + '...' + contact.profile.coinAddress[-8:]
        detailBody = detailBody + "    Coin Address: %s\n" % coinAddress
        if (contact.profile.lastUpdate == None):
            detailBody = detailBody + "    Last Update: UNKNOWN\n"
        else:
            detailBody = detailBody + "    Last Update: %s" % contact.profile.lastUpdate.getDisplayTime()
    else:
        detailBody = detailBody + "Profile: None\n"
    if (contact.profile.avatar != None):
        avatarAttachmment = Attachment(configPath=account.configPath, localPath=contact.profile.avatar)
    else:
        avatarAttachmment = None
    account.messages.sendMessage(recipients=commandGroup, body=detailBody, attachments=avatarAttachmment)
    return

def sendMessage(account:Account, commandGroup:Group, contactId:int, message:str, attachment:Optional[Attachment]) -> None:
    contact = account.contacts[contactId]
    account.messages.sendMessage(recipients=contact, body=message, attachments=attachment)
    account.messages.sendMessage(recipients=commandGroup, body="Message sent.")
    return

def sendHelpMessage(account:Account, commandGroup:Group, param:str) -> None:
    if (param.lower() == "none" or param.lower() == 'help'):
        helpBody = "Help:\n"
        helpBody = helpBody + "Methods: listContacts, contactDetail, send, help\n"
        helpBody = helpBody + "Note: all method names are case insensitive."
        helpBody = helpBody + "Enter key 'param':'methodName' for detailed help."
        account.message.sendMessage(recipients=commandGroup, body=helpBody)
    elif (param.lower() == 'listcontacts'):
        helpBody = "Help listContacts:\n"
        helpBody = helpBody + "List all contacts."
        helpBody = helpBody + "Params: None."
    elif (param.lower() == 'contactdetail'):
        helpBody = "Help contactDetail:\n"
        helpBody = helpBody + "Display details of a contact."
        helpBody = helpBody + "Params: contactid(int), Required, Contact id given by listContacts"
    elif (param.lower() == 'send'):
        helpBody = "Help send:\n"
        helpBody = helpBody + "Send a message to a contact.\n"
        helpBody = helpBody + "Params: contactid(int), required, contact id given by listcontacts.\n"
        helpBody = helpBody + "        message(str), required, message body to send.\n"
        helpBody = helpBody + "        attachment(str), optional, path to a file on the chatbot server.\n"
    else:
        helpBody = "Help: Invalid parameter: %s" % param
    
    account.messages.sendMessage(recipients=commandGroup, body=helpBody)


    return

def receivedMessageCb(account:Account, message:ReceivedMessage) -> None:
    print("Message received.")
    print("Marking read.")
    message.markRead()
    commandGroup = account.groups.getByName('Command & Control')
    if (message.recipientType != 'group' or message.recipient != commandGroup):
        print ("Message not in command and control group, relaying.")
        relayNotificationBody = "Relaying message.\nFrom: %s\nTo: %s" % (
                                                                        message.sender.getDisplayName(),
                                                                        message.recipient.getDisplayName()
                                                                    )
        account.messages.sendMessage(recipients=commandGroup, body=relayNotificationBody)
    # relay message:
        account.messages.sendMessage(recipients=commandGroup, body=message.body, attachments=message.attachments,
                                        sticker=message.sticker)
        return  
    # Make sure I'm mentioned:
    if (message.mentions.contactMentioned(account.contacts.getSelf()) == False):
        print("I'm not mentioned, doing Nothing.")
        return
    mention = message.mentions.getByContact(account.contacts.getSelf())[0]
# Parse json:
    try:
        commandStr = message.body.strip()
    # Remove mention:
        commandStrStart = commandStr[:mention.start] 
        commandStrEnd = commandStr[mention.start + mention.length:]
        commandStr = commandStrStart + commandStrEnd
        print("DEBUG: ", commandStr)
    # Convert json:
        commandMsg:dict[str, object] = json.loads(commandStr)
    except json.JSONDecodeError as e:
        message.react(THUMBS_DOWN)
        quote = message.getQuote()
        messageBody = "Message is not json. Doing nothing. Reason: %s" % e.msg
        print("DEBUG: ", messageBody)
        account.messages.sendMessage(recipients=commandGroup, body=messageBody, quote=quote)
        return
# Make sure method is in the command:
    if ('method' not in commandMsg.keys()):
        message.react(THUMBS_DOWN)
        quote = message.getQuote()
        account.messages.sendMessage(recipients=commandGroup, body="Invalid command, method not defined.")
        return
# Clean up method:
    method = stripWhiteSpace(commandMsg['method'])
    method = method.lower()

# List contaccts:
    if (method == 'listcontacts'):
        message.react(THUMBS_UP)
        listContacts(account, commandGroup)
# Contact details:
    elif (method == 'contactdetail'):
    # Argument check contact detail
        if ('contactid' not in commandMsg.keys()):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body="Missing required parameter: contactId(int)",
                                            quote=quote)
            return
        elif (isinstance(commandMsg['contactid'], int) == False):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body="type error: contactid not int", quote=quote)
            return
        elif (commandMsg['contactid'] > len(account.contacts)):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body="index error: contact id out of range", quote=quote)
            return
    # Send contact details:
        contactDetail(account, commandGroup, commandMsg['contactid'])
# Send message:
    elif (method == 'send'):
        if ('contactid' not in commandMsg.keys()):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body = "Missing required parameter: contactid(int)",
                                            quote=quote)
            return
        elif (isinstance(commandMsg['contactid'], int) == False):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body="type error: contactid not int", quote=quote)
            return
        elif (commandMsg['contactid'] > len(account.contacts)):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body="index error: contact id out of range", quote=quote)
            return
        elif ('message' not in commandMsg.keys()):
            message.react(THUMBS_DOWN)
            quote = message.getQuote()
            account.messages.sendMessage(recipients=commandGroup, body="Missing required parameter: message(str)",
                                            quote=quote)
            return
        if ('attachment' in commandMsg.keys()):
            attachmentPath = commandMsg['attachment']
            if (os.path.exists(attachmentPath) == False):
                message.react(THUMBS_DOWN)
                quote = message.getQuote()
                account.messages.sendMessage(recipients=commandGroup, body="attachment path doesn't exist.", quote=quote)
                return
            attachment = Attachment(configPath=account.configPath, localPath=commandMsg['attachment'])
        else:
            attachment = None
        sendMessage(account, commandGroup, commandMsg['contactid'], commandMsg['message'], attachment)
# Display Help:
    elif ('help' in commandMsg.keys()):
        if ('param' in commandMsg.keys()):
            sendHelpMessage(account, commandGroup, commandMsg['param'])
        else:
            sendHelpMessage(account, commandGroup, "None")
    else:
        message.react(THUMBS_DOWN)
        quote = message.quote()
        errorBody = "Invalid method: %s" % method
        account.messages.sendMessage(recipients=commandGroup, body=errorBody, quote=quote)
    return






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
    response = account.messages.sendMessage(recipients=commandGroup, body="Chatbot v%s started." % VERSION)
    sentMessage = response[0][2]
    
    sentMessage.react('🇨🇦')
    signal.startRecieve(account, receivedMessageCallback=receivedMessageCb)
    response = account.messages.sendMessage(recipients=commandGroup, body="Chatbot now accepting commands.")
    sentMessage = response[0][2]
    sentMessage.react('🤖')

    try:
        while (QUIT == False):
            pass
    except KeyboardInterrupt:
        signal.stopReceive(account)
        return

    account.messages.sendMessage(recipients=commandGroup, body="Chatbot shutting down.")

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="My chat bot.")
    parser.add_argument("--account", help="--account NUMBER, account number to use.", required=True)
    parser.add_argument("--group", help="--group GROUP_ID, Command and control group ID.")
    args = parser.parse_args()

    try:
        signal = SignalCli()
    except Exception as e:
        print(str(e.args))
        print("Failed to start signal.")
        exit(2)
    
    main(args, signal)
    signal.stopSignal()
    