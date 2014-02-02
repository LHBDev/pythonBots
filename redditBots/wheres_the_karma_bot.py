'''
Where's_the_karma_bot reads through comments, looking for the
phrase "karma5:" followed by a redditor's username. It will then post
the top 5 subreddit's where the user has received the most karma.

This is free software and you are free to redistribute and/or modify it
under the terms of the GNU General Public License, version 3 or later.

This program is distributed without any warranty; without even the implied
warranty of merchantability or fitness for a particular purpose.
'''

import praw
import time
import operator
import threading
import urllib2
from multiprocessing.pool import ThreadPool
from authentication import USERNAME, PASSWORD

pool = ThreadPool(processes=1)
delayedComments = []

#Login
r = praw.Reddit('Karma breakdown Bot by u/elotro v 1.5'
                'github.com/LHBDev/pythonBots/redditBots')
r.login(USERNAME, PASSWORD)

footer = "\n ** \n Delivered by a bot!\n **"
#read old ids
with open('oldIDs.txt', 'r') as f:
    oldReplies = [line.strip() for line in f]

#save new ids
def save_id(comment):
    with open('oldIDs.txt', 'a') as fi:
        fi.write(comment.id + "\n")
        fi.close()

def send_reply(comment, reply):
    try:
        comment.reply(reply)
        oldReplies.append(comment.id)
    except Exception as e:
        if "you are doing that too much" in str(e):
            delayedComments.append((reply, comment))
            time.sleep(300)


#check comment against saved IDs
#borrowed from Relec: github.com/Relec/autodefinition
def check_comment(comment):
    if comment.id not in oldReplies:
        comment1 = comment.body.lower()
        if ":" in comment1:
            param, value = comment1.split(":", 1)
            value = value.strip()
            value = value.split(' ', 1)[0]
            if not value == "":
                value = value.replace(" ", "")
                async_result = pool.apply_async(lookup_user, (value,))
                res = async_result.get()
                #print res
                if res != "Not found":
                    res = print_pretty(res)
                    threading.Thread(target=send_reply, args=(comment, res)).start()
                    threading.Thread(target=save_id, args=(comment,)).start()


#change dictionary into printable string
def print_pretty(res):
    width = 25
    align = (">", "<")
    title = ("Subreddit", "Karma")
    fin = "{title[0]:{align[0]}{width}} | {title[1]:{align[1]}{width}}\n"\
           .format(title=title, align=align, width=width)
    fin += "{0:^{width}}\n".format("-" * width, width=width * 2 + 1)
    for sub, karma in res:
        fin += "{sub:{align[0]}{width}} | {karma:{align[1]}{width}}\n"\
                .format(sub=sub, karma=karma, width=width, align=align)
    fin += "\n"
    fin += footer
    return fin


#calculate the karma by subreddit for Redditor
def calculate_karma(user, limit, thing):
    karma_by_sub = {}
    gen = (user.get_comments(limit) if thing == "comments" else
           user.get_submitted(limit))
    for stuff in gen:
        sub = stuff.subreddit.display_name
        karma_by_sub[sub] = (karma_by_sub.get(sub, 0) + stuff.ups - stuff.downs)
    return karma_by_sub

#sort the dictionary and keep top 5
def sort_and_cut(dic, limit):
    return sorted(dic.iteritems(), key=operator.itemgetter(1), reverse=True)[:limit]


#look through Redditor's comment and posting history
#and add up karma, grouped by subReddit
def lookup_user(name):
  user = r.get_redditor(name)
  break_by = ['comments', 'submissions']
  try:
      for thing_type in break_by:
          #extra sleep time since we are making another
          #request from the server
          time.sleep(120);
          karma = calculate_karma(user, 100, thing_type)
          karma = sort_and_cut(karma, 5)
          return karma
  except urllib2.HTTPError:
      return "Not Found"


def handle_delayed():
        message = delayedComments.pop()
        rep = message[0]
        comm = message[1]
        send_reply(comm, rep)


def loop():

    while True:
        if delayedComments:
            if len(delayedComments) > 10:
                while delayedComments:
                    handle_delayed()
                    time.sleep(600)
            else:
                handle_delayed()
        else:
            try:
                #grab comments
                submissions = r.get_subreddit('LHBDevbottestsub').get_top(limit=20)
                for submission in submissions:
                    for comment in submission.comments:
                        #check if comment is calling our bot
                        if "karma5:" in comment.body.lower():
                            threading.Thread(target=check_comment, args=(comment,)).start()

                #Sleep 5 minutes so we don't overload Reddit's servers
                time.sleep(300)
            except Exception as e:
                print(e)

main_thread = threading.Thread(target=loop)
main_thread.start()
