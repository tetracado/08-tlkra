from email.parser import BytesParser
from email.policy import default
import imaplib
import quopri
import typing as t
import re
import tlkrahid
import schedule
import textwrap
import time
from atproto import Client, models,client_utils

def extract_url_byte_positions(text: str, *, encoding: str = 'UTF-8') -> t.List[t.Tuple[str, int, int]]:
    """This function will detect any links beginning with http or https."""
    #https://github.com/MarshalX/atproto/blob/main/examples/advanced_usage/auto_hyperlinks.py
    encoded_text = text.encode(encoding)

    # Adjusted URL matching pattern
    pattern = rb'https?://[^ \n\r\t]*'

    matches = re.finditer(pattern, encoded_text)
    url_byte_positions = []

    for match in matches:
        url_bytes = match.group(0)
        url = url_bytes.decode(encoding)
        url_byte_positions.append((url, match.start(), match.end()))

    return url_byte_positions

def injecturls(text: str):

    url_positions = extract_url_byte_positions(text)
    facets = []

    for link_data in url_positions:
        uri, byte_start, byte_end = link_data
        facets.append(
            models.AppBskyRichtextFacet.Main(
                features=[models.AppBskyRichtextFacet.Link(uri=uri)],
                index=models.AppBskyRichtextFacet.ByteSlice(byte_start=byte_start, byte_end=byte_end),
            )
        )
    return facets

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
            
            testmessage=thisemail[0][1]
            #print('thismessage',thismessage)
            emailparser=BytesParser(policy=default)

            #fix quopri bullshit
            qpmessage=quopri.decodestring(testmessage) #this one sometimes fucks up
            thismessage=emailparser.parsebytes(qpmessage)
            if thismessage.get("Subject")==None or thismessage.get("From")==None:
                   print('FAILED QUOPRI DETECTED, MANUALLY AVOIDING QUOPRI')
                   thismessage=emailparser.parsebytes(testmessage)
            
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
                if len(parts)>5:
                    print("FAILED PARTS TOO LONG MUST BE FAILED PARSE")
                else:
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
        print('ready to post with parts',parts)
        hashremove=parts[0][14:] #remove    {#TLKRiderAlert}
        firstpost=models.create_strong_ref(bskyclient.send_post(text=client_utils.TextBuilder().tag('#TLKRiderAlert','TLKRiderAlert').text(hashremove),facets=injecturls(parts[0])))
        postloop(parts[1:],firstpost,firstpost)
    else: #midloop
        postloop(parts[1:],models.create_strong_ref(bskyclient.send_post(text=parts[0],facets=injecturls(parts[0]),reply_to=models.AppBskyFeedPost.ReplyRef(parent=prevpost,root=parentpost))),parentpost)


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
    print('type message in processmkessage',type(message))
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
    #print(message)
    #print(type(message))
    #print(message.items())
    content=message.get_payload()
    #print('unchecked content',content)
    #print(type(content))
    if type(content)!=type('pspp'): #not string 
        content=content[0].get_content()
    print('checked content',content)
    try:
        alert=re.findall("((.|\n)*)In\sEffect", content)[0][0] #for in effect, normal emails
    except:
        alert=re.findall("((.|\n)*)\nUpdated: ", content)[0][0] #for emails without "in effect" in them 
    #print(type(alert))
    #print('alert',alert)
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