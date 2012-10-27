# -*- coding: utf-8 -*-
'''
Created on 2010-03-20

@author: mdk
'''
import logging, email, time, imaplib, sqlite3, os, re
from time import gmtime, strftime
from imaplib import *
from smtplib import *
from pyza.config import TESTING_DIR, PROBLEMS_DIR, ROOT_DIR
from tempfile import mktemp
from pyza.data import Task
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart, MIMEBase
from os import path as PATH
from fnmatch import fnmatch
from email import Encoders
from email.header import decode_header

# TODO: EMAIL SETUP GOES HERE
IMAP_SERVER = ''
IMAP_SERVER_PORT = 993
MAIL_USER = ''
MAIL_PASS = ''
SMTP_SERVER = ''
SMTP_PORT = 25

QUEUE_MAILBOX = 'INBOX'
OK_MAILBOX = 'OK'
ERR_MAILBOX= 'ERR'
PROBLEMS_MAILBOX = 'PROBLEMS'

CMD_TASKLIST = 'ZADANIA'
CMD_RESULTS = 'WYNIKI'
CMD_RANKING = 'RANKING' # not implemented
CMD_ADDTASK = 'ADDTASK' # not implemented

SQLITE3_DB = PATH.join(ROOT_DIR, 'pyza.db')

MESSAGE_CHECK_DELAY = 10
FILE_SIZE_LIMIT = 100 * 1024 # 100 Kb

log = logging.getLogger('EmailQueue')

#imaplib.Debug = 4

M = None

def getConnection():
    global M
    if M is not None: return M
    M = IMAP4_SSL(IMAP_SERVER, IMAP_SERVER_PORT)
    M.login(MAIL_USER, MAIL_PASS)
    return M

def problemExists(problemid):
    pdir = os.path.join(PROBLEMS_DIR, problemid)
    return os.path.exists(pdir)

class TaskListEmpty(Exception): pass

class IncorrectUserid(Exception): pass

class FileTooLongError(Exception): pass

class ProblemNotFoundError(Exception): pass

class CommandProcessed: pass

#retrieveMail = retrieveMailFile

def sendMsg(to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = MAIL_USER
    msg['To'] = to
    S = SMTP(SMTP_SERVER, SMTP_PORT);
    #S.login(MAIL_USER, MAIL_PASS);
    S.sendmail(MAIL_USER, [to], msg.as_string())
    S.quit()

def serveTaskListCmd(userid, subject):
    global log
    log.info("TaskList request from %s" % userid)
    msg = "Witaj,\n\nOto lista dostępnych zadań:\n"
    for task in os.listdir(PROBLEMS_DIR):
        msg = msg + ' * ' + task + '\n'
    msg = msg + "\n--\nWyślij wiadomość z tematem '%s <problem_name>', aby otrzymać treść zadania" % CMD_TASKLIST
    sendMsg(userid, "Re: %s" % subject, msg)

def serveTaskDescriptionCmd(userid, subject):
    global log
    # retrieve problem id
    problemid = subject[len(CMD_TASKLIST):].strip()
    log.info('Task Description Request %s for %s' % (problemid, userid))
    if not problemExists(problemid):
        log.error("Problem %s doesn't exists" % str(problemid))
        return
    # list all PDFs from problem dir
    files = os.listdir(PATH.join(PROBLEMS_DIR, problemid))
    pdfs = []
    for file in files:
        if fnmatch(file, "*.pdf"):
            pdfs.append(file)
    # construct message
    msg = MIMEMultipart()
    msg['Subject'] = 'Re: %s' % subject
    msg['From'] = MAIL_USER
    msg['To'] = userid
    body = "Witaj,\n\nTreść zadania %s znajdziesz w załączniku\n" % problemid
    # add message content    
    msg.attach( MIMEText(body))
    # add message atachments
    for f in pdfs:
        part = MIMEBase('application', "octet-stream")
        with open(PATH.join(PROBLEMS_DIR, problemid, f), "rb") as fp:
            part.set_payload(fp.read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % f)
        msg.attach(part)
    # send message
    S = SMTP(SMTP_SERVER, SMTP_PORT);
    #S.login(MAIL_USER, MAIL_PASS);
    S.sendmail(MAIL_USER, [userid], msg.as_string())
    S.quit()

def serveResultsCmd(userid, subject):
    global log
    M = getConnection()
    M.select(OK_MAILBOX)
    res, ids = M.search(None, '(FROM "%s")' % str(userid))
    results = {}
    if res == 'OK' and len(ids[0].split()) > 0: 
        res, data = M.fetch((','.join(ids[0].split())), "(BODY[HEADER.FIELDS (SUBJECT)])")
        if res == 'OK':
            for msg in data:
                if len(msg) > 1 and msg[1].startswith('Subject'):
                    problemid = msg[1].split()[1]
                    if problemid not in results: results[problemid] = [0,0]
                    results[problemid][0] += 1
    M.select(ERR_MAILBOX)
    res, ids = M.search(None, '(FROM "%s")' % str(userid))
    if res == 'OK' and len(ids[0].split()) > 0: 
        res, data = M.fetch((','.join(ids[0].split())), "(BODY[HEADER.FIELDS (SUBJECT)])")
        if res == 'OK':
            for msg in data:
                if len(msg) > 1 and msg[1].startswith('Subject'):
                    problemid = msg[1].split()[1]
                    if problemid not in results: results[problemid] = [0,0]
                    results[problemid][1] += 1
    msg = "Witaj,\n\nOto twoje dotychczasowe wyniki:\n"
    for key, res in results.iteritems():
        msg += " * %s - " % key
        if res[0] > 0: msg += 'OK'
        else: msg += 'ERR'
        if res[1] > 0: msg += ' (%d)' % res[1]
        msg += '\n'
    sendMsg(userid, 'Re: %s' % subject, msg)

def serveRankingCmd():
    pass # not implemented

def serveAddTaskCmd():
    pass

def getSingleTask():
    global log
    M = getConnection()
    # lock na M
    # TODO: nalezy popatrzec sie na polecenia
    # TODO: nalezy popatrzec sie na liste problemow
    M.select(QUEUE_MAILBOX)
    msg, msgid = None, None
    type, data = M.search(None, 'UNSEEN')
    msgs = data[0].split()
    if len(msgs) > 0:
        msgid = msgs[0]
        type, data = M.fetch(msgid, '(RFC822)')
        M.store(msgid, '+FLAGS', '\Seen')
        for rp in data:
            if isinstance(rp, tuple):
                msg = email.message_from_string(rp[1])
    if msg is None: raise TaskListEmpty()
    
    fromaddr = msg.get('From')
    subject = decode_header(msg.get('Subject'))[0][0].strip().translate(None, '.\\/')
    userid = fromaddr[fromaddr.find('<') + 1:fromaddr.find('>')]
    
    if len(userid) < 5: raise IncorrectUserid()
    if not problemExists(subject):
        if subject == CMD_TASKLIST: pass
        elif subject.startswith(CMD_TASKLIST): serveTaskDescriptionCmd(userid, subject)
        elif subject == CMD_RESULTS: serveResultsCmd(userid, subject)
        elif subject == CMD_RANKING: serveRankingCmd()
        elif subject == CMD_ADDTASK: serveAddTaskCmd()
        else:
            log.error("Could not found instruction for subject '%s'" % subject)
            raise ProblemNotFoundError()
        log.debug("Remove message %s" % str(msgid))
        M.select(QUEUE_MAILBOX)
        M.store(msgid, '+FLAGS', '\Deleted')
        M.expunge()
        raise CommandProcessed()
    
    log.debug("New message retrieved (Subj '%s', From '%s')", subject, userid)
    # TODO: sprawdzic jeszcze rozmiar
    attname = None
    att = None
    for part in msg.walk():
        attname = decode_header(part.get_filename())[0][0]
        att = part.get_payload(decode=1)
    if len(att) > FILE_SIZE_LIMIT: raise FileTooLongError()
    suffix = attname[attname.rfind('.'):]
    filename = mktemp(suffix=suffix, dir=TESTING_DIR)
    with open(filename, 'w') as f:
        f.write(att)
    
    task = Task(subject, userid, filename)
    task.msgid = msgid
    log.debug("New task created for problem '%s', user '%s' (file %s)",
              subject, userid, filename)
    return task

def prepareMsg(task, result):
    return '''Witaj,

Twoje rozwiązanie zadania '%s' zostało ocenione przez system testujący.

Wynik: %s

Dodatkowe informacje: %s''' % (task.problemid, result.code, result.cases)

def storeResult(task, result):
    con = sqlite3.connect(SQLITE3_DB)
    query = 'INSERT INTO results(uid, problemid, date, result, log) VALUES("%s","%s","%s","%s","%s");' % \
        (str(task.userid), str(task.problemid), strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()), str(result.code), \
         str(result.cases))
    log.debug('Execute query %s' % query)
    con.execute(query)
    con.commit()
    con.close()


def saveResult(task, result):
    M = getConnection()
    # lock na M
    M.select('INBOX')
    dst = ERR_MAILBOX
    if result.code == 'OK': dst = OK_MAILBOX
    M.copy(task.msgid, dst)
    M.store(task.msgid, '+FLAGS', '\Deleted')
    M.expunge()
    log.debug('Send result [%s] to %s', result.code, task.userid)
    sendMsg(task.userid, 'Re: %s' % task.problemid, prepareMsg(task,result))
    storeResult(task, result)

def getTask():
    while True:
        try:
            task = getSingleTask()
            return task
        except TaskListEmpty:
            log.debug('No tasks on mailbox')
        except CommandProcessed:
            continue
        time.sleep(10)

