from chatgpt_wrapper import ChatGPT
import datetime
import sqlite3
import subprocess
import time
import json
import os
bot = ChatGPT()
mode=""

def init():
    # clear screen
    os.system('clear')

    # ask the user which mode to use, auto or manual
    mode = "manual"
    mode = input("Auto or Manual mode? Default Manual (auto/manual): ")

    #ask if they have a contacts.json file
    contacts = "no"
    contacts = input("have a cleanContacts.json file? Enter the file path here, otherwise hit enter to continue): ")

    #ask the user for the path of their iMessage database
    path = input("What is the path to your iMessage database? (/Users/userName/Messages/chatDB): ")
    path = "/Users/kellygold/Library/Messages/chat.db"
    
    return[path, mode]

def select_conversation(recent_messages):
    #Show the unique phone numbers of the people you have recently texted and ask the user to choose one using numbers
    print("Here are the people you have recently texted: ")
    unique_phone_numbers = set([message['phone_number'] for message in recent_messages])
    count=0
    all = []
    for i, phone_number in enumerate(unique_phone_numbers):
        #open contacts.json and check if phone_number = ZFULLNUMBER, if so, print ZFIRSTNAME and phone_number
        with open('cleanContacts.json') as f:
            data = json.load(f)
            for p in data:
                if count >=10:
                    break
                if p['FULLNUMBER'] == phone_number:
                    count=count+1
                    print(count, p['FIRSTNAME'] + ': ' + phone_number)
                    # add p to all
                    all.append(p)
                    break
                # Need to add handling for numbers that are not in contacts.json
                # I decided to only show the first 10 people in contacts.json
                # else:
                #     count=count+1
                #     print(count, ': ' + phone_number)
                #     # add p to all
                #     all.append(p)
                #     break

        # print(i, phone_number)
    choice = int(input("Which person would you like to text? (enter a number): "))
    phone_number = all[choice-1]['FULLNUMBER']
    print("You have selected: " + all[choice-1]['FIRSTNAME'] + "," + phone_number)
    return [phone_number, all[choice-1]['FIRSTNAME']]

def filter_messages(messages, phone_number, person):
    # Filter messages where phone_number is phone_number
    filtered_messages = [message for message in messages if message['phone_number'] == phone_number]
    for message in filtered_messages:
        if message['is_from_me'] == True:
            message['sender'] = " Kelly: "
        else:
            message['sender'] = person + ": "
    return filtered_messages

def check_last_sender(messages):
    last_sender = messages[0]['sender']
    print ("The last sender was: " + last_sender)
    return last_sender

def ask_chatGPT(prompt):
    response = bot.ask(prompt)
    # print(response)
    return response

def get_recent_messages(chat_db, mode):
    # Phone number or label for "you"
    self_number = "Me"
    # Number of messages to return
    n = 400
    # Read the messages
    messages = read_messages(chat_db, n,mode, self_number=self_number, human_readable_date=True)
    return messages


def read_messages(db_location, n, mode, self_number='Me', human_readable_date=True):
    conn = sqlite3.connect(db_location)
    cursor = conn.cursor()

    query = """
    SELECT message.ROWID, message.date, message.text, message.attributedBody, handle.id, message.is_from_me, message.cache_roomnames
    FROM message
    LEFT JOIN handle ON message.handle_id = handle.ROWID
    """

    if n is not None:
        query += f" ORDER BY message.date DESC LIMIT {n}"

    results = cursor.execute(query).fetchall()
    messages = []

    for result in results:
        rowid, date, text, attributed_body, handle_id, is_from_me, cache_roomname = result

        if handle_id is None:
            phone_number = self_number
        else:
            phone_number = handle_id

        if text is not None:
            body = text
        elif attributed_body is None:
            continue
        else:
            attributed_body = attributed_body.decode('utf-8', errors='replace')

            if "NSNumber" in str(attributed_body):
                attributed_body = str(attributed_body).split("NSNumber")[0]
                if "NSString" in attributed_body:
                    attributed_body = str(attributed_body).split("NSString")[1]
                    if "NSDictionary" in attributed_body:
                        attributed_body = str(attributed_body).split("NSDictionary")[0]
                        attributed_body = attributed_body[6:-12]
                        body = attributed_body

        if human_readable_date:
            date_string = '2001-01-01'
            mod_date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
            unix_timestamp = int(mod_date.timestamp())*1000000000
            new_date = int((date+unix_timestamp)/1000000000)
            date = datetime.datetime.fromtimestamp(new_date).strftime("%Y-%m-%d %H:%M:%S")
            
        messages.append(
            {"rowid": rowid, "date": date, "body": body, "phone_number": phone_number, "is_from_me": is_from_me,
             "cache_roomname": cache_roomname})
    conn.close()
    return messages

def askAndRespond(conversation_messages, person, mode):
    # Give chatGPT instructions and ask if it understands
    firstAsk = "Draft a response to a text message conversation between Kelly and "+person+". I will give you a JSON Array of the most recent message data. For each item in the array: the field 'date' is when the message was sent, the field 'body' is the message text. When the field 'is_from_me' equals 0, the message was sent by " + person + ". When the field 'is_from_me' equals 1 the message was sent from Kelly. Draft a response to the most recent message(s) from " + person + " as Kelly. Limit the draft to 280 characters, do not use Kelly or " + person + "'s name, only respond with the drafted text message and NO OTHER TEXT. Do not use quotes. Use informal language and match the style of other messages if possible. Make your response brief like a text message. I will first show you the message data, after you process them draft and output ONLY the drafted response. Do you understand? "
    #print(firstAsk)
    firstResponse = ask_chatGPT(firstAsk)
    #print(firstResponse)
    # Give chatGPT the conversation messages
    secondResponse = ask_chatGPT(json.dumps(conversation_messages[0:5]))
    rawSecondResponse = secondResponse.replace('"', '')
    if mode=="auto":
        print("Response accepted.")
        return rawSecondResponse
    print(rawSecondResponse)
    print('\n')
    checkWithUser = input("Is this the response you want to send? (y/n): ")
    print('\n')
    subtractor = 1
    while checkWithUser != "y" and subtractor  < 5:
        print("Generating a new response...")
        print('\n')
        altResponse = ask_chatGPT("generate a different response, shorten the response and only output response text")
        rawSecondResponse = altResponse.replace('"', '')
        print(rawSecondResponse)
        print('\n')
        checkWithUser = input("Is this the response you want to send? (y/n): ")
        subtractor = subtractor + 1
    if checkWithUser=="y":
        print("Response accepted.")
    else:
        print("No good responses were generated. Please run the program again.")
        exit()
    return rawSecondResponse
        
def sender(phone_number, response):
    file_path = os.path.abspath('imessage_tmp.txt')
    with open(file_path, 'w') as f:
        f.write(response)
        command = f'tell application "Messages" to send (read (POSIX file "{file_path}") as «class utf8») to buddy "{phone_number}"'
    subprocess.run(['osascript', '-e', command])
    print("Message sent! \n")


### CORE LOGIC ###
config = init()
initialMessages = get_recent_messages(config[0], config[1])
conversation_phone_number = select_conversation(initialMessages)
while True:
    recent_messages = get_recent_messages(config[0], config[1])
    conversation_messages = filter_messages(recent_messages, conversation_phone_number[0], conversation_phone_number[1])
    if check_last_sender(conversation_messages) == " Kelly: ":
        print("You were the last sender... Waiting for a response...")
        print('\n')
        time.sleep(60)
        os.system('clear')
    else:
        print("You were not the last sender... Sending a message...")
        print('\n')
        replyMessage = askAndRespond(conversation_messages, conversation_phone_number[1], config[1])
        sender(conversation_phone_number[0], replyMessage)
        time.sleep(60)
        os.system('clear')
