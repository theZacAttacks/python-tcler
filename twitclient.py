#!/usr/bin/env python2
#
# Copyright (c) 2013, theZacAttacks
#
#
# A simple little twitter client written using the python-twitter
#  module and tcl for a GUI.
#
# Version       Changelog
#-------------------------------------------------------------------------------
# 0.1           original tcl gui code written
#
# 0.2           got the unique api code hardcoded
#
# 0.4           added threads to improve GUI performace
#
# 0.6           changed a lot of the display code to make it more
#                robust and applicable
#
# 0.8           can pull tweets from timeline, can post tweets
#                tweet's author is easily distenguished from tweets
#
# 0.9           tweets displayed accuratly, autoupdating works and 
#                character counting works
#
# 0.9.1         GUI resizes correctly, and took out the hard coded
#                values of my creds and made it check ~/.tcler for
#                the user's key & token. 
#               IDEAS: make links clickable. scan through each tweet
#                that comes in, and make each hyperlink clickable. (DONE)
#
# 0.9.2         Links now clickable, added menu item to open every link
#                Fixed the new tweet display error
#
# 0.9.3         Added some error handling for character for the Tkinter 
#                Text widget
#
# 0.9.4         Added a console option. This prints out the errors/thread
#                info that typically gets printed to the console to a 
#                GUI window for users not running from console. Also
#                https links now work
#               IDEAS: make ERR a list that contains the backlog of errors
#                and/or messages. Make console display the backlog of
#                errors whenever it gets started
#
# 0.9.5         All messages/errors are stored in ERR which is now a global 
#                list. When the console is started the backlog of messages
#                (stored in ERR) is vomited into the console. These backlog
#                messages are greyed out, whereas the new messages are 
#                not greyed.
#
# 0.9.6         Clicking a user's handle (the text in red) will now fill
#                out the 'post' box with their username, allowing easier
#                tweets at a person. Also, incorporated tkHyperLinkManager
#                into the main file.
#               IDEAS: Make the hashtags clickable which opens a Toplevel
#                box that lists the search results. Incorporate a search
#                function into the client itself, accessable via a menu
#                button. 

import twitter
import threading
import webbrowser

from Tkinter import *
from os import path
from urllib2 import URLError
from time import sleep
from time import localtime
from platform import system

#
# GLOBAL VARIABLE DECLARATION
#

# log of errors
global ERR
ERR = list()

# bool that helps stop the threads
global STREAM_UPDATE
STREAM_UPDATE = True

# the id of the last tweet
global LAST_ID
LAST_ID = None

# Tkinter StringVar (used for updating the character count
global TEXT
TEXT = None

# conDialog reference that is used for checks
global CON
CON = None

# class that helps handle the task of managing the various 'clicky' actions for text
class HyperlinkManager:
        
        def __init__(self, text):
                
                self.text = text
                
                self.text.tag_config("hyper", foreground="blue", underline=1)
                
                self.text.tag_bind("hyper", "<Enter>", self._enter)
                self.text.tag_bind("hyper", "<Leave>", self._leave)
                self.text.tag_bind("hyper", "<Button-1>", lambda x: self._click("hyper"))
                
                self.text.tag_config("handle", foreground="red")
                self.text.tag_bind("handle", "<Button-1>", lambda x: self._click("handle"))
                
                self.reset()
        def reset(self):
                self.links = {}
        def add(self, action, text, thisTag):
                tag = thisTag + "-%d" % len(self.links)
                self.links[tag] = (action,text)
                return thisTag, tag
        def _enter(self, event):
                self.text.config(cursor="hand2")
        def _leave(self, event):
                self.text.config(cursor="")
        def _click(self, thisTag, event = None):
                for tag in self.text.tag_names(CURRENT):
                        if tag[:(len(thisTag) + 1)] == thisTag + "-":
                                self.links[tag][0](self.links[tag][1])
                                return

# a simple class that allows for a Toplevel widget to become active with the console log
class conDialog(Toplevel):
        def __init__(self, parent, title):
                self.top = Toplevel(parent)
                self.top.wm_title(title)
                self.top.wm_minsize(width=200, height=250)
                
                self.parent = parent
                
                self.running = True
                
                self.logger = Text(self.top, width=50, height=15)
                self.logger.pack(fill=BOTH, expand=1)
                self.logger.config(wrap=WORD)
                
                self.close = Button(self.top, text="Close", command=self.closeThisWindow)
                self.close.pack(fill=X,expand=0)
                
                self.logger.tag_config('backlog', foreground="grey")
                
                for e in ERR:
                        self.logger.insert(INSERT, e + "\n", 'backlog')
                
                self.placeText(getTime() + "- Console Started")
                
                self.logger.config(state=DISABLED)

        # destroys this Toplevel widget while making note of the console closing
        #  and by setting the CON variable to None
        def closeThisWindow(self):
                self.placeText(getTime() + "- Console closed")
                
                self.top.destroy()
                global CON
                CON = None
                
        # method that places the text inside the log thats in the console
        #  also stores the messages in the backlog (ERR)
        def placeText(self, message):
                self.logger.config(state=NORMAL)
                ERR.append(message)
                self.logger.insert(INSERT, message + "\n")
                self.logger.config(state=DISABLED)

# class that instantiates a thread which, based off of the name, thread id and arguments
#  does certain jobs
class upThread (threading.Thread):
        def __init__(self, threadID, name, args):
                threading.Thread.__init__(self)
                self.threadID = threadID
                self.name = name
                
                if name == "update":
                        self.tweet_id = args
                elif name == "numbers":
                        self.entry = args
                elif name == "post":
                        self.tweet_id = args
                
        # starts the threads while making a note in the backlog/console
        def run(self):
                if CON != None and not self.threadID < 2:
                        CON.placeText(getTime() + "- " + self.name + "-" + str(self.threadID) + " starting...")
                elif self.threadID < 2:
                        ERR.append(getTime() + "- " + self.name + "-" + str(self.threadID) + " starting...")
                elif CON == None and not self.threadID < 2:
                        ERR.append(getTime() + "- " + self.name + "-" + str(self.threadID) + " starting...")
                else:
                        print(self.name + " starting...")
                if self.name == "update":
                        if self.tweet_id != 1:
                                update(0, self.tweet_id)
                        else:
                                update(1,LAST_ID)
                elif self.name == "numbers":
                        numbers(self.entry)
                elif self.name == "post":
                        post()
                if CON != None and not self.threadID < 2:
                        CON.placeText(getTime() + "- " +self.name + "-" + str(self.threadID) + " exiting...")
                elif CON == None and not self.threadID < 2:
                        ERR.append(getTime() + "- " + self.name + "-" + str(self.threadID) + " exiting...")
                else:
                        print(self.name + " exiting...")
        
        # returns the name of the thread
        def getName(self):
                return(self.name)
        

# updates the text in the text widget with supplied tuple(?) of
#  statuses. 
#
#  DO NOT CHANGE, unless you have a good reason (which I always have a good reason)
def updateDisplay(status):
        text.config(state=NORMAL)
        
 #       withNewLine = 0
        newStat = "< > "
        counter = 1.0
        
        text.insert(counter, "\n")
        
        for s in reversed(status):
                try:
                        if s != status[0]:
                                newStat = "\n<" + s.user.screen_name + "> "
#                                withNewLine = 1
                        else:
                                newStat = "<" + s.user.screen_name + "> "
                        length = len(newStat)/100
                        for word in reversed(s.text.split(' ')):
                                if word.split(':')[0] == 'http' or word.split(':')[0] == 'https':
                                        text.insert(counter, " ")
                                        text.insert(counter, word, hyper.add(clickLink, word, "hyper"))
                                else:
                                        text.insert(counter, word + " ")
                        
                        text.insert(counter, newStat, hyper.add(clickAuthor, newStat, "handle"))
                
                except TclError:
                        if CON != None:
                                CON.placeText(getTime() + "- A Tcl Character error occured, the offending tweet wasn't displayed")
                        else:
                                print "A Tcl Character error occured, the offending tweet wasn't displayed"
        
        text.config(state=DISABLED)


# starts a thread that runs a one-shot update on statuses.
#  this method, like the postThread method, is mainly
#  so the GUI doesn't freeze up while the method runs
def oneShotUpdate():
        one_update = upThread(3, "update", 1)
        one_update.start()

# 
def clickAuthor(handle):
        handle = handle.split('<')[1].split('>')[0]
        entry.insert(INSERT, "@" + handle + " ")

# supplies the callback to open links in the default
#  web browser
def clickLink(link):
        webbrowser.open(link)

# shows the console toplevel widget
def showConsole():
        if CON != None:
                CON.placeText(getTime() + "- Console already shown")
        else:
                global CON
                CON = console = conDialog(root, "Console")

# posts the status updates
def post():
        toPost = entry.get()
        entry.delete(0, END)
        
        api.PostUpdate(toPost)

# keeps track of the chacter count and updates the GUI label 
def numbers(entry):
        while STREAM_UPDATE:
                global TEXT
                TEXT.set(140 - len(entry.get()))
                sleep(.1)

# just an easy method that makes it easier to get the
#  current local time in the correct format
def getTime():
        return str(localtime().tm_hour) + ":" + str(localtime().tm_min) + ":" + str(localtime().tm_sec) + " "

# quits the threads and destroys the widgets
def quit(thread):
        
        if CON != None:
                CON.closeThisWindow()
        
        global STREAM_UPDATE
        STREAM_UPDATE = False
        
        thread.join()
        
        root.destroy()

# starts a thread to run the post function. (Made this just so the GUI 
#   doesn't unattractivly freeze up
def postThreader():
        post_thread = upThread(2,"post",0)
        post_thread.start()

# gets the newest updates, while trying to stay within the Twitter's API
#   rate limit. has two modes, 0 and 1. 1 is just a one time thing, while
#   0 drops into a loop that checks every minute for new updates. 0 is meant
#   for the update thread and nothing else, while 1 is meant for the update
#   button.
def update(shot, last_id):
        if shot != 1:
                counter = 0
                while STREAM_UPDATE:
                        STATUSES = list()
                        try:
                                STATUSES = api.GetHomeTimeline(since_id=last_id)
                                if len(STATUSES) != 0:
                                        last_id = STATUSES[0].id
                                
                                if len(STATUSES) > 0 and LAST_ID != last_id:
                                        global LAST_ID
                                        LAST_ID = last_id
                                        updateDisplay(STATUSES)
                                
                                for i in range(18):
                                        sleep(5)
                                        if STREAM_UPDATE != True:
                                                break
                                                
                                if STREAM_UPDATE != True:
                                        break
                        except twitter.TwitterError:
                                if CON != None:
                                        CON.placeText(getTime() + "- There was a Twitter problem getting the tweets")
                                else:
                                        print "There was a Twitter problem getting the tweet"
                                for i in range(18):
                                        sleep(5)
                                        if STREAM_UPDATE != True:
                                                break
                                                
                                if STREAM_UPDATE != True:
                                        break
                        except URLError:
                                if CON != None:
                                        CON.placeText(getTime() + "- There was a network issue when getting the tweets")
                                else:
                                        print "There was a network issue when getting the tweets"
                                for i in range(18):
                                        sleep(5)
                                        if STREAM_UPDATE != True:
                                                break
                                                
                                if STREAM_UPDATE != True:
                                        break
                        
        else:
                try:
                        STATUSES = ()
                        STATUSES = api.GetHomeTimeline(since_id=last_id)
                
                        if len(STATUSES) > 0:
                                global LAST_ID
                                LAST_ID = STATUSES[0].id
                                updateDisplay(STATUSES)
                except twitter.TwitterError:
                        if CON != None:
                                CON.placeText(getTime() + "- There was a Twitter problem getting the tweets")
                        else:
                                print "There was a Twitter problem getting the tweet"
                except URLError:
                        if CON != None:
                                CON.placeText(getTime() + "- There was a network issue when getting the tweets")
                        else:
                                print "There was a network issue when getting the tweets"

# creates the access_token secret and key variables to use to get the api reference
ASS_KEY = None
ASS_SECRET = None

# sets the local err variable to None, meaning that no errors have happened yet.
#  this is used because ERR is already set to not be None, so ERR != None will 
#  always return True
err = None

# OS checking code. (NOTE: Untested. Hopefully it works)
if system() == "Windows":
        if not path.exists(path.expanduser('%APPDATA%\tcler.txt')):
                import get_access_token
else:
        # this assumes that if you aren't on windows, then
        #  you are running some Unix based system (including
        #  OS X)
        if not path.exists(path.expanduser('~/.tcler')):
                import get_access_token
        
# gets the user's creds and splits the key and secret up
red = open(path.expanduser('~/.tcler'), 'r').read().split('\n')
ASS_KEY = red[0]
ASS_SECRET = red[1]

# get the API reference
api = twitter.Api(consumer_key='qJwaqOuIuvZKlxwF4izCw',
		  consumer_secret='53dJ9tHJ77tAE8ywZIEU60JYPyoRU9jY2v0d58nI8',
		  access_token_key=ASS_KEY,
		  access_token_secret=ASS_SECRET)

# no statuses either
STATUSES = None

# try and get the statuses, while catching either a network error 
#  or a twitter error
try:
        STATUSES = api.GetHomeTimeline()
except URLError:
        if err == None:
                err = list()
        
        ERR.append(getTime() + "- There was a problem opening the network connection. Please ensure that your computer is online.")
        err.append(ERR[len(ERR)-1])
except twitter.TwitterError:
        if err == None:
                err = list()
        
        ERR.append(getTime() + "- Your timeline could not be retrieved at this time.\nPlease try again later.")
        err.append(ERR[len(ERR)-1])

# tries to start a thread that just constantly runs the update function
#  (see the update function docs for more info)
try:
        UPDATE_THREAD = upThread(0, "update", LAST_ID)
        
        UPDATE_THREAD.start()
except:
        if err == None:
                err = list()
        
        ERR.append(getTime() + "- Streaming update thread failed to start. Updating will have to be done manually.")
        err.append(ERR[len(ERR)-1])

# 
# STARTS SETTING UP TK GUI STUFF
#
root = Tk()
root.wm_title("Python Tcler - Twitter Client")
root.wm_minsize(width=200,height=400)

global TEXT
TEXT = StringVar(root)

scroll = Scrollbar(root)
scroll.pack(side=RIGHT, fill=Y,expand=0)

text = Text(root, yscrollcommand=scroll.set)
text.config(state=DISABLED, wrap=WORD)
text.pack(fill=BOTH, expand=1)
#text.tag_config("a", foreground="red")

hyper = HyperlinkManager(text)

post_button = Button(root, text="Post", command=postThreader)
post_button.pack(side=RIGHT, fill=BOTH, expand=0)

Label(root, textvariable=TEXT).pack(side=RIGHT)

entry = Entry(root)
entry.pack(fill=X, expand=1 ,side=RIGHT)

scroll.config(command=text.yview)

menu = Menu(root)
menu.add_command(label="Update", command=oneShotUpdate)
menu.add_command(label="Console", command=showConsole)
menu.add_command(label="Quit", command=lambda: quit(UPDATE_THREAD))
root.config(menu=menu)
#
# END OF TK GUI STUFF
#

# tries to start the number thread to keep track of the
#  character count
try:
        NUMBER_THREAD = upThread(1, "numbers", entry)
        NUMBER_THREAD.start()
except:
        if err == None:
                err = list()
        
        ERR.append(getTime() + "- Starting the thread for numbers failed. Character counting will not be operational")
        err.append(ERR[len(ERR)-1])

# if the local variable err is still None, then no errors 
#  occured since start up, otherwise a message is printed 
#  saying to check the log (which, when opened will be 
#  populated with all of the error messages, or otherwise,
#  that will hopefully help the user find the problem)
if err != None:
        text.config(state=NORMAL)
        text.insert(1.0, "Something has gone wrong, please check the console")

# tries to start a thread that will keep the character count
#  see the docs on the numbers function

ERR.append(getTime() + "- Main window started")

root.mainloop()
