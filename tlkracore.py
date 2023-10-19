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
    #try:
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
                    continue
                (alert, subject)=details
                tweettext="#TRRiderAlert: "+subject+" | "+alert
                print('got tweettext:',tweettext)
            except Exception as error:
                print(f'An error occurred during message processing: {error}')
            try: 
                parts=getparts(tweettext)
                if len(parts)==1:
                    root_post_ref=models.create_strong_ref(bskyclient.send_post(text=tweettext))
                elif len(parts)==2:
                    root_post_ref=models.create_strong_ref(bskyclient.send_post(text=parts[0]))
                    reply_to_ref0=models.create_strong_ref(bskyclient.send_post(text=parts[1],reply_to=models.AppBskyFeedPost.ReplyRef(parent=root_post_ref,root=root_post_ref)))
                else:
                    print('post too longgg, lenparts='+len(parts))
            except Exception as error:
                print(f'An error occurred during tweet posting: {error}')
            mailclient.store(message, '+X-GM-LABELS', '\\Trash')
           
        mailclient.close()
        mailclient.logout()

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
    content=message.get_payload()[0].get_content()
    print(content)
    alert=re.findall("((.|\n)*)In Effect", content)[0][0]
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

#checkmail()

schedule.every(5).minutes.do(checkmail) 

while True:
    schedule.run_pending()
    time.sleep(1)