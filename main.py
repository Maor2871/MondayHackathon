import datetime
import imaplib
from time import strptime
import re
import email
import json
import pickle
from email.header import decode_header
import os
import sklearn
import mimetypes
from monday import *


def get_sender(email):
    """
    if the mail is from moodle, get the sender name.
    """
    try:
        email = email.split("על ידי")
        sender = email[1]
        sender = sender.split("/")[0]
        if "בתאריך" in sender:
            sender = sender.split("בתאריך")[0]
        if "<" in sender:
            sender = sender.split("<")[0]
        sender = sender.replace("\r\n", "")
        return sender
    except:
        # print(email)
        return "Bot"


def index_of_value(lst, value):
    for i in range(len(lst)):
        if lst[i] == value:
            return i + 1


def algo(email):
    model, cv = pickle.load(open(r"spam_detection_model.pkl", 'rb'))
    return model.predict(cv.transform([email])).item()


def clean(text):
    try:
        return "".join(c if c.isalnum() else "_" for c in text)
    except:
        return None


def write_files(name, content_type, part):
    wrote_files = []
    """
    little explanation:
    we are getting files content type in mime. we need to convert it to the needed format. eg:
    image/jpeg  ---> .jpg
    application/vnd.openxmlformats-officedocument.presentationml.presentation  ---> .pptx

    in addition, we want to save the files without erasing the older files- so we need to give every file
    a unique name
    """
    n = 0
    name1 = name
    file_names = [f.split(".")[0] for f in os.listdir('.') if os.path.isfile(f)]

    while name in file_names:
        name = name1 + str(n)
        n += 1
    with open(name + mimetypes.guess_extension(content_type), "wb") as f:
        wrote_files.append(name + mimetypes.guess_extension(content_type))
        f.write(part.get_payload(decode=True))
    return wrote_files


def fetch_emails(username, password):
    dictos = {}
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(username, password)
    status, messages = imap.select("INBOX")
    lst_of_dictos = []

    # number of top emails to fetch:
    N = 100
    messages = int(messages[0])
    for i in range(messages, messages - N, -1):
        # fetch the email message by ID
        res, msg = imap.fetch(str(i), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    try:
                        subject = subject.decode(encoding)
                    except:
                        pass
                        #print("lost this email")  # usually these are spam emails
                From, encoding = decode_header(msg.get("From"))[0]

                # Extract the date.
                date = msg.get("date")
                # print(date)
                if "," in date:
                    date = date.split(",")[1]
                    date = date.split(" ")

                    day = date[1]
                    month = date[2]
                    year = date[3]
                else:
                    date = date.split(" ")

                    day = date[0]
                    month = date[1]
                    year = date[2]

                month = str(strptime(month, '%b').tm_mon)

                if len(day) == 1:
                    day = '0' + day
                if len(month) == 1:
                    month = '0' + month

                dictos["date:"] = year + '-' + month + '-' + day
                dictos["files"] = []


                if isinstance(From, bytes):
                    if encoding is not None:
                        From = From.decode(encoding)
                # print("Subject:", subject)
                # print("From:", From)
                dictos["From"] = From
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            # print(body)
                            try:

                                dictos["subject"] = subject + ", "
                                dictos["email"] = body
                                lst_of_dictos.append(dictos)
                                # dictos = {}
                            except:
                                pass
                        elif "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                try:
                                    name = clean(subject)

                                    dictos["files"] = write_files(name, content_type, part)
                                    # lst_of_dictos.append(dictos)
                                    # dictos = {}
                                except:
                                    pass
                                    #print("lost this too")  # usually these are spam emails
                else:
                    # extract content type of email
                    content_type = msg.get_content_type()
                    # get the email body
                    body = msg.get_payload(decode=True).decode()
                    if content_type == "text/plain":
                        # print only text email parts
                        # print(body)
                        dictos["subject"] = subject + ", "
                        dictos["email"] = body
                        lst_of_dictos.append(dictos)
                        # dictos = {}
                if content_type == "text/html":

                    folder_name = clean(subject)

                    filename = "index.html"
                    try:
                        if not folder_name:
                            continue
                        filepath = os.path.join(folder_name, filename)
                    except:
                        pass  # :)
                        # print(folder_name, filename)
                        # exit(99)
                    # write the file
                    if "<style" in body:  # checking if that's a real html message, not accidentally recognized as one.
                        name = clean(subject) + ".html"
                        with open(name, "w", encoding="utf-8") as f:
                            f.write(body)
            dictos = {}

            # print("=" * 4)
    # close the connection and logout
    imap.close()
    imap.logout()
    return lst_of_dictos


def add_course(item_name):
    """
        The function receives a course name and updates the dictionary with mails.
    """

    # The list of mails.
    global lst_of_dictos

    # The name of the course.
    course_name = item_name

    # The final list with all the emails connected to the received course.
    course_mails = []

    # Iterate over the mails.
    for mail in lst_of_dictos:

        mail_subject = mail["subject"]
        mail_content = mail["email"]

        # If the current mail relates to the course, save it in the list.
        if course_name in mail_content or course_name in mail_subject:
            mail["course"] = course_name
            course_mails.append(mail)

    # Create a new group for the current course.
    courses_board.add_group(Group(board=courses_board, title=course_name))

    # Iterate over the mails again.
    for email in course_mails:

        # --- Extract zoom link ---

        mail_links = email["URLs"]

        zoom_link = None

        # Look for zoom link in the urls.
        for mail_link in mail_links:
            if 'zoom' in mail_link:
                zoom_link = mail_link
                if "www.google.com" in zoom_link:
                    zoom_link = zoom_link.replace("https://www.google.com/url?q=", "")
                break

        # --- Add the mail to monday ---

        # Add the mail to the course in monday.
        courses_board.groups[course_name].add_item(
            Item(group=courses_board.groups[course_name], name=email["subject"],
                 columns_values=[("From", email["From"]), ("Date", email["date:"])]))

        # Add the content of the mail as update.
        courses_board.groups[course_name].items[email["subject"]].add_update(
            email["email"])

        # If there is a zoom link add it.
        if zoom_link:
            # Add a zoom link reference to the current mail.
            courses_board.groups[course_name].items[email["subject"]].add_link(
                column_title="Zoom link", link=zoom_link, description="")

        # Add the attached files, zoom links and contents of the mails.
        courses_board.groups[course_name].items[email["subject"]].upload_files(
            column_title="Attached Files", files_paths=email["files"])


def create_inbox(board, mails_list):
    """
        The function adds all the mail to the inbox board.
    """

    for email in mails_list:

        mail_links = email["URLs"]

        # --- Extract the zoom link if exists ---
        zoom_link = None

        # Look for zoom link in the urls.
        for mail_link in mail_links:
            if 'zoom' in mail_link:
                zoom_link = mail_link
                if "www.google.com" in zoom_link:
                    zoom_link = zoom_link.replace("https://www.google.com/url?q=", "")
                break

        # Add the mail to the course in monday.
        board.groups["Inbox"].add_item(
            Item(group=board.groups["Inbox"], name=email["subject"],
                 columns_values=[("From", email["From"]), ("Date", email["date:"])]))

        # Add the content of the mail as update.
        board.groups["Inbox"].items[email["subject"]].add_update(
            email["email"])

        # If there is a zoom link add it.
        if zoom_link:
            # Add a zoom link reference to the current mail.
            board.groups["Inbox"].items[email["subject"]].add_link(
                column_title="Zoom link", link=zoom_link, description="")

        # Add the attached files, zoom links and contents of the mails.
        board.groups["Inbox"].items[email["subject"]].upload_files(
            column_title="Attached Files", files_paths=email["files"])


def create_secretariat(board, secretariat_mails):
    """
        The function adds all the mail to the inbox board.
    """

    for email in secretariat_mails:

        mail_links = email["URLs"]

        # --- Extract the zoom link if exists ---
        zoom_link = None

        # Look for zoom link in the urls.
        for mail_link in mail_links:
            if 'zoom' in mail_link:
                zoom_link = mail_link
                if "www.google.com" in zoom_link:
                    zoom_link = zoom_link.replace("https://www.google.com/url?q=", "")
                break

        # Add the mail to the course in monday.
        board.groups["Secretariat"].add_item(
            Item(group=board.groups["Secretariat"], name=email["subject"],
                 columns_values=[("From", email["From"]), ("Date", email["date:"])]))

        # Add the content of the mail as update.
        board.groups["Secretariat"].items[email["subject"]].add_update(
            email["email"])

        # If there is a zoom link add it.
        if zoom_link:
            # Add a zoom link reference to the current mail.
            board.groups["Secretariat"].items[email["subject"]].add_link(
                column_title="Zoom link", link=zoom_link, description="")

        # Add the attached files, zoom links and contents of the mails.
        board.groups["Secretariat"].items[email["subject"]].upload_files(
            column_title="Attached Files", files_paths=email["files"])


def create_importance(board, mails_list):
    """
        The function receives mails list and adds it to the importance board.
    """
    #print("mails list:", mails_list)
    five, four, three, two, one = [], [], [], [], []
    importance_dict = {1: one, 2: two, 3: three, 4: four, 5: five}

    # Iterate over all the mails and order them by starts
    for email in mails_list:

        importance_dict[email['importance']].append(email)

    # The mails by the importance order.
    mails_by_importance = five + four + three + two + one

    # Now the mails are ordered. Iterate over them by order.
    for email in mails_by_importance:

        # --- Extract the zoom link if exists ---
        mail_links = email["URLs"]

        zoom_link = None

        # Look for zoom link in the urls.
        for mail_link in mail_links:
            if 'zoom' in mail_link:
                zoom_link = mail_link
                if "www.google.com" in zoom_link:
                    zoom_link = zoom_link.replace("https://www.google.com/url?q=", "")
                break

        # Add the mail to the course in monday.
        board.groups["Mails"].add_item(
            Item(group=board.groups["Mails"], name=email["subject"],
                 columns_values=[("From", email["From"]), ("Date", email["date:"])]))

        # Add the content of the mail as update.
        board.groups["Mails"].items[email["subject"]].add_update(
            email["email"])

        # If there is a zoom link add it.
        if zoom_link:

            # Add a zoom link reference to the current mail.
            board.groups["Mails"].items[email["subject"]].add_link(
                column_title="Zoom link", link=zoom_link, description="")

        # Add the attached files, zoom links and contents of the mails.
        board.groups["Mails"].items[email["subject"]].upload_files(
            column_title="Attached Files", files_paths=email["files"])

        # Update the rating of the mail.
        board.groups["Mails"].items[email["subject"]].set_rating(column_title="Importance", value=str(email["importance"]))


def create_zoom_links(board, zoom_links):
    """
        The function creates the zoom links board.
    """

    # Add all the zoom links to the zoom board.
    for zoom_link in zoom_links:

        # Add the mail to the course in monday.
        board.groups["Zooms"].add_item(
            Item(group=board.groups["Zooms"], name=zoom_link["From"], columns_values=[("Date", zoom_link["Date"])]))
        board.groups["Zooms"].items[zoom_link["From"]].add_link(column_title="Link", link=zoom_link["Link"],
                                                                description=zoom_link["Link"])


if __name__ == "__main__":

    print("Loading mails, please wait...")

    # --- Real all mails ---

    # Check if already loaded mails before.
    # try:
    # with open("last.txt", "r") as f:
    # last = json.load(f)
    # except Exception as e:
    # with open("last.txt", "w") as f:
    # f.write("")
    # last = ""

    # Account credentials:
    username = "idanisrael@mail.tau.ac.il"
    password = "rlitkzzeocishvek"
    lst_of_dictos = fetch_emails(username, password)
    # print(lst_of_dictos)
    # print(lst_of_dictos)

    # Data to analyze.
    urls = []
    courses = []

    # A list of all the secretariat mails.
    list_of_secretariat_mails = []

    # A list with all the zoom links and their columns data.
    # form: [{"link": zoom link, "From": the name of who sent the mail with the zoom link, "Date": the data of the mail}].
    zoom_links_data = []

    # Analyze the mails.
    # print(lst_of_dictos)
    for i in range(len(lst_of_dictos)):

        try:
            if "noreply" in lst_of_dictos[i]["From"]:
                lst_of_dictos[i]["From"] = get_sender(lst_of_dictos[i]["email"])
            lst_of_dictos[i]["From"] = lst_of_dictos[i]["From"].replace("\r\n", "")
            lst_of_dictos[i]["From"] = lst_of_dictos[i]["From"].replace("\n", "")
        except:
            pass
        urls = []
        course = "Not Detected"

        lst_of_dictos[i]["subject"] = lst_of_dictos[i]["subject"].replace('Fwd: ', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\r\n', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\r', "")

        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\n', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\u202c', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\u202a', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\u200f', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('"', "")
        lst_of_dictos[i]["subject"] = lst_of_dictos[i]["subject"].replace('"', "")
        # lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('\\', "")
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].split('צפיה בהודעה זו בהקשר שלה')[0]
        lst_of_dictos[i]["email"] = re.sub('\[.*?\]|<.*?>', '', lst_of_dictos[i]["email"])
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                          lst_of_dictos[i]["email"])
        #  this is here to erase all the links from the message after saving them. may want to delete this:
        lst_of_dictos[i]["email"] = re.sub(
            'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            "", lst_of_dictos[i]["email"])
        for w in range(len(urls)):
            urls[w] = urls[w].strip("-")

        lst_of_dictos[i]["URLs"] = urls
        for t in range(len(urls)):
            urls[t] = urls[t].replace("Meeting", "")
        a = lst_of_dictos[i]["email"]
        for k in courses:
            if k in a:
                course = k
        lst_of_dictos[i]["course"] = course
        # print(a)

        if "בתאריך" in a:
            a = a.split("בתאריך")
            a = a[1]

        # a = a.split("צפיה בהודעה זו בהקשר שלה")
        # a = a[0]
        new_str = ''
        put = "yes"
        # removing unwanted moodle links:
        for j in a:
            if j != "<" and put == "yes":
                new_str += j
            else:
                put = "no"

            if j == ">":
                put = "yes"
        lst_of_dictos[i]["email"] = new_str
        # print(lst_of_dictos[i]["email"])

        # Add all the secretariat mails.
        if "secretariat" in str(lst_of_dictos[i]["From"]).lower():
            list_of_secretariat_mails.append(lst_of_dictos[i])

        # Save the zoom link if exists in the zoom links dictionary.
        mail_links = lst_of_dictos[i]["URLs"]

        # Find the zoom link.
        zoom_link = None

        # Look for zoom link in the urls.
        for mail_link in mail_links:
            if 'zoom' in mail_link:
                zoom_link = mail_link
                if "www.google.com" in zoom_link:
                    zoom_link = zoom_link.replace("https://www.google.com/url?q=", "")
                break

        # Add the zoom link if exists.
        if zoom_link:
            zoom_links_data.append({"Link": zoom_link, "From": lst_of_dictos[i]["From"],
                                    "Date": lst_of_dictos[i]["date:"]})

        try:
            lst_of_dictos[i]["importance"] = algo(new_str)
        except Exception as e:
            print(e)
            lst_of_dictos[i]["importance"] = "Error"
            print("error in algo")

        lst_of_dictos[i]["email"] = re.sub("Forwarded message From:.*?Subject:", "", lst_of_dictos[i]["email"])
        lst_of_dictos[i]["subject"] = re.sub("Forwarded message From:.*?Subject:", "", lst_of_dictos[i]["subject"])
        lst_of_dictos[i]["email"] = re.sub("To:.*?ac\.il", "", lst_of_dictos[i]["email"])
        lst_of_dictos[i]["subject"] = re.sub("To:.*?ac\.il", "", lst_of_dictos[i]["subject"])
        lst_of_dictos[i]["email"] = lst_of_dictos[i]["email"].replace('-', "")

    # Find the new mails.
    # if last in lst_of_dictos:
    # lst_of_dictos = lst_of_dictos[index_of_value(lst_of_dictos, last):]


    # try:
    # last = lst_of_dictos[-1]
    # except:
    # last = last
    # with open("last.txt", "w") as f:
    # f.write(json.dumps(last))

    # All data collected.
    print("All mails loaded successfully.")
    print()
    print("Updating data in monday.")

    # Create the workspace.
    work_space = WorkSpace(name="test",
                           token="eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjE2MDE2NDI2NiwidWlkIjoyOTk1NzM4OCwiaWFkIjoiMjAyMi0wNS0xMlQwNzozNzozNi43NThaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTE4NzU5MjIsInJnbiI6InVzZTEifQ.wWCFkrSi-Mo_cFnsyVgFrKEjcVGQwezYYQ_GyPTS92k",
                           print_api_protocol=False)

    # --- Input Board

    # Create a new input board.
    input_board = InputBoard(ws=work_space, name="Input", execution_dict={'Courses': add_course})

    # Create input groups.
    for input_type in ["Courses"]:
        # Create a group for the current input type.
        input_board.add_group(Group(board=input_board, title=input_type))

    # --- Inbox Board ---
    inbox_board = ThreadBoard(ws=work_space, name="Inbox", exists=False, thread_function=create_inbox,
                              function_parameters={"mails_list": lst_of_dictos})

    # Create columns for the inbox board.
    inbox_board.add_column(
        Column(board=inbox_board, title="From", description="Who sent the mail", column_type="text"))
    inbox_board.add_column(
        Column(board=inbox_board, title="Date", description="When the email was received", column_type="date"))
    inbox_board.add_column(
        Column(board=inbox_board, title="Zoom link", description="Links in the mail message", column_type="link"))
    inbox_board.add_column(
        Column(board=inbox_board, title="Attached Files", description="All the files attached to this mail",
               column_type="file"))

    # Create a group for the current input type.
    inbox_board.add_group(Group(board=inbox_board, title="Inbox"))

    # Start adding all the mails to the inbox board.
    inbox_board.start()

    # --- Secretariat Board ---

    secretariat_board = ThreadBoard(ws=work_space, name="Secretariat", exists=False, thread_function=create_secretariat,
                              function_parameters={"secretariat_mails": list_of_secretariat_mails})

    # Create columns for the inbox board.
    secretariat_board.add_column(
        Column(board=secretariat_board, title="From", description="Who sent the mail", column_type="text"))
    secretariat_board.add_column(
        Column(board=secretariat_board, title="Date", description="When the email was received", column_type="date"))
    secretariat_board.add_column(
        Column(board=secretariat_board, title="Zoom link", description="Links in the mail message", column_type="link"))
    secretariat_board.add_column(
        Column(board=secretariat_board, title="Attached Files", description="All the files attached to this mail",
               column_type="file"))

    # Create a group for the current input type.
    secretariat_board.add_group(Group(board=secretariat_board, title="Secretariat"))

    # Start adding all the mails to the inbox board.
    secretariat_board.start()

    # --- Importance Board ---

    importance_board = ThreadBoard(ws=work_space, name="Importance", exists=False, thread_function=create_importance,
                                   function_parameters={"mails_list": lst_of_dictos})

    # Create columns for the importance board.
    importance_board.add_column(
        Column(board=importance_board, title="From", description="Who sent the mail", column_type="text"))
    importance_board.add_column(
        Column(board=importance_board, title="Date", description="When the email was received", column_type="date"))
    importance_board.add_column(
        Column(board=importance_board, title="Importance", description="5- very important, 1- you'd like to ignore",
               column_type="rating"))
    importance_board.add_column(
        Column(board=importance_board, title="Zoom link", description="Links in the mail message", column_type="link"))
    importance_board.add_column(
        Column(board=importance_board, title="Attached Files", description="All the files attached to this mail",
               column_type="file"))

    # Create groups for the importance groups.
    importance_board.add_group(Group(board=importance_board, title="Mails"))

    # Start adding all the mails to the importance board.
    importance_board.start()

    # --- Zoom Links Board ---

    zoom_links_board = ThreadBoard(ws=work_space, name="Zoom Links", exists=False, thread_function=create_zoom_links,
                                   function_parameters={"zoom_links": zoom_links_data})

    # Create columns for the inbox board.
    zoom_links_board.add_column(
        Column(board=zoom_links_board, title="Link", description="The link to the zoom meeting",
               column_type="link"))
    zoom_links_board.add_column(
        Column(board=zoom_links_board, title="Date", description="When the email was received", column_type="date"))

    # Create a group for the current input type.
    zoom_links_board.add_group(Group(board=zoom_links_board, title="Zooms"))

    # Start adding all the mails to the inbox board.
    zoom_links_board.start()

    # --- Courses Board ---

    # Create a new board for the courses.
    courses_board = Board(ws=work_space, name="Courses", exists=False)

    # Create columns for the courses board.
    courses_board.add_column(
        Column(board=courses_board, title="From", description="Who sent the mail", column_type="text"))
    courses_board.add_column(
        Column(board=courses_board, title="Date", description="When the email was received", column_type="date"))
    courses_board.add_column(
        Column(board=courses_board, title="Zoom link", description="Links in the mail message", column_type="link"))
    courses_board.add_column(
        Column(board=courses_board, title="Attached Files", description="All the files attached to this mail",
               column_type="file"))

    # Start listening to the input board.
    input_board.start()

    print("All boards created, please refresh the page.")
