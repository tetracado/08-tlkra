from email.parser import BytesParser
from email.policy import default
import imaplib
import quopri

import re
import tlkrahid
import tweepy
import schedule
import textwrap
import time
from bs4 import BeautifulSoup
from atproto import Client, models

def createmailclient(email_address, password):
    SMTP_SERVER="imap.gmail.com"
    SMTP_PORT=993

    mailclient=imaplib.IMAP4_SSL(host=SMTP_SERVER, port=SMTP_PORT)
    mailclient.login(email_address, password)
    print('logged in to email via imaplib')
    return mailclient

def checkmail(test=False):
    try:
        mailclient=createmailclient(tlkrahid.tlkraemail, tlkrahid.tlkrapass)
        mailclient.select('INBOX')
        typ, messages = mailclient.search(None, 'ALL')
        if not messages:
            print('No messages found.')
            return
        for message in messages[0].split():
            typ, thisemail = mailclient.fetch(message, '(RFC822)')
            typ, thisuid=mailclient.fetch(message, 'UID')
            print('uid:',thisuid)
            thismessage=thisemail[0][1]
            emailparser=BytesParser(policy=default)
            thismessage=quopri.decodestring(thismessage)
            thismessage=emailparser.parsebytes(thismessage)
            try: 
                details=processmessage(thismessage)
                if details==None:
                    print('got NONE as return for processmessage')
                    continue
                elif details==False:
                    mailclient.store(message, '+X-GM-LABELS', '\\Trash')    
                    continue
                print('got details',details)
                (alert, subject)=details
                tweettext="#TLKRiderAlert: "+subject+" | "+alert
                print('got tweettext:',tweettext)
                parts=getparts(tweettext)
                postloop(parts,False,False)
                mailclient.store(message, '+X-GM-LABELS', '\\Trash')
            except Exception as error:
                print(f'An error occurred during message processing: {error}')

           
        mailclient.close()
        mailclient.logout()
    except Exception as errortext:
        print('couldnt check mail with error code',errortext)

def postloop(parts, prevpost, parentpost):
    if len(parts)==0: #end of loop
        print('succesffuly posted tweet')
        return
    elif parentpost==False: #start of loop
        firstpost=models.create_strong_ref(bskyclient.send_post(text=parts[0]))
        postloop(parts[1:],firstpost,firstpost)
    else: #midloop
        postloop(parts[1:],models.create_strong_ref(bskyclient.send_post(text=parts[0],reply_to=models.AppBskyFeedPost.ReplyRef(parent=prevpost,root=parentpost))),parentpost)


def getparts(text):
    parts=textwrap.wrap(text,width=275)
    ntweets=len(parts)   
    ncount=0
    for part in parts:
        #print(ntweets)
        if ntweets ==1:
            continue
        else:
            parts[ncount]=part+'...'
            ncount+=1
            ntweets-=1
    return parts

def processmessage(message):
    subject=message.get("Subject")
    sender=message.get("From")
    print('got subject:', subject)
    print('got sender:', sender)
    if not "donotreply@alerts.translink.ca" in sender: #skip non-alert emails
        print('not a real alert email')
        return(None)
    if "cancelled" in subject: #skip cancellation emails
        print('cancellation email, deleting')
        return(False)
    content=message.get_payload()[0].get_content()
    print(content)
    alert=re.findall("((.|\n)*)In\sEffect", content)[0][0]
    print(type(alert))
    print(alert)
    alert=re.sub('\n',' ',alert)
    #print('alert:',alert)
    return (alert, subject)

def getparts(text):
    parts=textwrap.wrap(text,width=275)
    ntweets=len(parts)   
    ncount=0
    for part in parts:
        #print(ntweets)
        if ntweets ==1:
            continue
        else:
            parts[ncount]=part+'...'
            ncount+=1
            ntweets-=1
    return parts



bskyclient=Client()
bskyclient.login('tlkalertrepeater.bsky.social', tlkrahid.apppass)
print('logged in to bsky')

checkmail()

schedule.every(5).minutes.do(checkmail) 

while True:
    schedule.run_pending()
    time.sleep(1)