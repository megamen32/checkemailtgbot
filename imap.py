import imaplib
import logging
import re
import socket
import traceback
from contextlib import contextmanager
from email import message_from_bytes

import socks

class EmailException(Exception):pass
from get_browser import get_proxy #возвращает прокси формата адресс:порт


def get_imap_server(email):
    """Determine the IMAP server based on email domain."""
    rambler_domains = ['rambler.ru', 'myrambler.ru', 'rambler.ua', 'ro.ru',
                       'autorambler.ru', 'rambler.com','lenta.ru']
    mailru_domains = ['mail.ru', 'bk.ru', 'list.ru', 'inbox.ru','bizml.ru']
    fmail = ['fmaild.com', 'dfirstmail.com', 'sfirstmail.com']
    yamail = ['yandex.ru']

    if any([x in email for x in rambler_domains]):
        return imaplib.IMAP4_SSL('imap.rambler.ru')
    elif any([x in email for x in mailru_domains]):
        return imaplib.IMAP4_SSL('imap.mail.ru')
    elif any([x in email for x in fmail]):
        return imaplib.IMAP4('mail.firstmail.ru')
    elif any([x in email for x in yamail]):
        return imaplib.IMAP4_SSL('imap.yandex.ru')
    else:
        logging.error(f'uncown domain in {email}')
        return None

def extract_email_body(raw_email):
    """Extract body from raw email data."""
    message = message_from_bytes(raw_email)
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition and "text/plain" in content_type:
                return part.get_payload(decode=True).decode('utf-8')
        return None  # No suitable part found
    else:
        return message.get_payload(decode=True).decode('utf-8')

@contextmanager
def use_proxy(proxy):
    original_socket = socket.socket

    proxy_parts = proxy.split(':')
    ip = proxy_parts[0]
    port = int(proxy_parts[1])

    socks.set_default_proxy(socks.HTTP, ip, port)
    socket.socket = socks.socksocket
    try:
        yield
    finally:
        socket.socket = original_socket

def is_email_valid(email, password):
    proxy = get_proxy()
    with use_proxy(proxy):
        mail = get_imap_server(email)
        if not mail:
            return False


        mail.login(email, password)
        try:
            mail.logout()
        except:
            traceback.print_exc()

        return True


import socket

def check_email(email, password):
    proxy = get_proxy()
    with use_proxy(proxy):
        mail = get_imap_server(email)
        if not mail:
            return None

        try:
            mail.login(email, password)
            mail.select("inbox")

            result, data = mail.search(None, '(FROM "rutube@rutubeinfo.ru")')
            if result != 'OK':
                return None

            # Reverse the list of email IDs to start from the most recent
            email_ids = data[0].split()
            email_ids.reverse()

            for email_id in email_ids:
                result, email_data = mail.fetch(email_id, "(RFC822)")
                if result != 'OK':
                    continue

                email_body = extract_email_body(email_data[0][1])
                if not email_body:
                    continue

                # Enhanced regex for a potential confirmation code pattern
                match = re.search(r"(\d{4})", email_body)
                if match:
                    return [match.group(1)]
        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e} {email}")
            if (e.args[0] == b'Invalid login or password'):
                return EmailException(f"IMAP error {email}")
                raise EmailException(f"IMAP error {email}")
            else:
                return None
        finally:
            try:
                mail.logout()
            except:
                pass

    return None




if __name__=='__main__':
    email,password='ffouuzud@fmaild.com:@zdwithshX6373!@'.split(':')
    print(is_email_valid(email,password))