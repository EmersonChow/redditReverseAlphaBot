import praw 
import json 
from collections import Counter

punctuations = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''

def removePunctuations(word):
    no_punct = ""
    for char in word:
        if char not in punctuations:
            no_punct = no_punct + char

    return no_punct




def wordIsInReverse(word):
    prev = "z"
    for letter in word:
        if prev >= letter:
            prev = letter
        else:
            return False
    return True

def preprocessWord(word):
    return removePunctuations(word.lower())


def isReverseAlphabeticalOrder(comment):
    comment = comment.strip()

    fullComment = comment.split(" ")
    if len(fullComment) > 1:
        for word in fullComment:
            cleanWord = preprocessWord(word)
            if cleanWord:
                if wordIsInReverse(cleanWord) == False:
                    return False
            else:
                return False
        return True
    else:
        return False

#credit to https://github.com/acini/praw-antiabuse-functions
#This is simple collection of functions to prevent reddit bots from:
#1. replying twice to same summon
#2. prevent chain of summons
#3. have limit on number of replies per submission

#Note: See TODO and make according changes
#Note: You can use reply function like this: post_reply(comment-content,praw-comment-object)
#Note: is_summon_chain returns True if grandparent comment is bot's own
#Note: comment_limit_reached returns True if current will be 5th reply in same thread, resets on process restart
#Note: don't forget to decalre `submissioncount = collections.Counter()` before starting your main loop
#Note: Here, r = praw.Reddit('unique client identifier')

def is_summon_chain(r, post, username):
  if not post.is_root:
    parent_comment_id = post.parent_id
    parent_comment = r.get_info(thing_id=parent_comment_id)
    if parent_comment.author != None and str(parent_comment.author.name) == username: #TODO put your bot username here
      return True
    else:
      return False
  else:
    return False

def comment_limit_reached(post):
    #20 per thread seems ok since this bot should rarely be called.
  global submissioncount
  count_of_this = int(float(submissioncount[str(post.submission.id)]))
  if count_of_this > 20: #TODO change the number accordingly. float("inf") for infinite (Caution!)
    return True
  else:
    return False
  
def is_already_done(username, post):
    done = False
    numofr = 0
    try:
        repliesarray = post.replies
        numofr = len(list(repliesarray))
    except:
        pass
    if numofr != 0:
        for repl in post.replies:
            if hasattr(repl, "author") and hasattr(repl.author, "name") and repl.author.name == username: #TODO put your bot username here
                done = True
                continue
    if done:
        return True
    else:
        return False

def post_reply(reply,post):
    global submissioncount
    try:
        a = post.reply(reply)
        submissioncount[str(post.submission.id)]+=1
        return True
    except Exception as e:
        print(f"REPLY FAILED: {e} @ {post.subreddit}")
        if str(e) == '403 Client Error: Forbidden':
            print(f"/r/{post.subreddit} has banned me")
            #save_changing_variables()
            with open("blackListedSubReddits.json", "r") as infile:
                blackList = json.load(infile)
                blackList[post.subreddit.display_name] = True
            
            with open("blackListedSubReddits.json", "w") as outfile: 
                json.dump(blackList, outfile)

            with open("subRedditsToCheck.json", "r") as infile:
                toCheck = json.load(infile)
                try:
                    toCheck.pop(post.subreddit.display_name)
                except KeyError as ke:
                    print("CheckList doesn't contain blacklistsubreddit: {post.subreddit.display_name}. Exception {ke}")
            
            with open("subRedditsToCheck.json", "w") as outfile: 
                json.dump(toCheck, outfile)
            
        return False

def openRedditInstance(accountSpecs):
    with open(accountSpecs, "r") as read_file:
        data = json.load(read_file)
    
    try:
        reddit = praw.Reddit(
            client_id= data["clientId"],
            client_secret= data["secret"],
            user_agent= data["userAgent"],
            username= data["username"],
            password= data["password"],
        )
        return (data["username"], reddit)

    except Exception as e:
        print("Could not sign into Reddit. Error: {e}")
        raise Exception

def updateData(savedData):
    with open("savedData.json", "w") as outfile:
        json.dump(savedData, outfile)

def isBretheren(comment, otherUsername):
    if hasattr(comment, "author") and hasattr(comment.author, "name") and comment.author.name == otherUsername:
        return True
    else:
        return False



if __name__ == "__main__":
    username, reddit = openRedditInstance("accountSpecs.json")

    with open("savedData.json", "r") as read_file:
        savedData = json.load(read_file)
    
    submissioncount = Counter()
    with open("blackListedSubReddits.json", "r") as infile:
        blackList = json.load(infile)
    
    with open("subRedditsToCheck.json", "r") as infile:
        toCheck = json.load(infile)

    toAdd = []

    for subredditName in toCheck.keys():
        subreddit = reddit.subreddit(subredditName)
        for submission in subreddit.hot(limit=10):
            if blackList.get(submission.subreddit.display_name) == None:
                if len(toCheck.keys()) <= 100 and toCheck.get(submission.subreddit.display_name) == None:
                    toAdd.append(submission.subreddit.display_name)

                for comment in submission.comments.list():
                    if hasattr(comment, "body"):
                        if not is_already_done(username, comment) and not comment_limit_reached(comment):

                            savedData["commentsChecked"] += 1
                            if isReverseAlphabeticalOrder(comment.body):
                                savedData["reverseComments"] += 1
                                reply = f"Would you look at that, all of the words in your comment are in reverse alphabetical order.\n\nI have checked {savedData['commentsChecked']} comments, and only {savedData['reverseComments']} of them were in reverse alphabetical order."
                                post_reply(reply,comment)
                            elif isBretheren(comment, "alphabet_order_bot"):
                                savedData["timesMetAlphabeticalOrderBot"] += 1
                                reply = f"Hello u/alphabet_order_bot, we meet again. It's been {savedData['timesMetAlphabeticalOrderBot']} times. I hope you have a great day!"
                                post_reply(reply,comment)

                            

    updateData(savedData)

    for subreddit in toAdd:
        toCheck[subreddit] = True
    with open("subRedditsToCheck.json", "w") as outfile:
        json.dump(toCheck, outfile)



