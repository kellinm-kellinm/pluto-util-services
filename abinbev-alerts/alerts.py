from getpass import getpass
import smtplib
from email.message import EmailMessage
import time
import os
import sys
import math
import logging

from gsheets import Sheets
import argparse

from pluto_wrapper import PlutoClient


os.chdir(os.path.dirname(sys.argv[0]))

SHEET_NAME = "1WIysm6o-lZOXBrk4097llUwTqLa_P1SEeM5arZXSZsk"
DATA_START = "2020-03-17T23:00:00.000Z"
SMTP_HOST = "localhost"

EMAIL_ADDRESS = "notifications@plutoshift.com"
PASSWORD = "2Jx4pDBkQPExEqXQyd5IrK"
SLEEP_TIME = 0  # They upload 5 minutes pass the hour, we poll at 6. with crontab
logger = logging.getLogger()


class AlertObject:
    def __init__(self, plant_name, asset, kpi_name, upper_threshold=math.inf, lower_threshold=0, *args):
        self.ro_name = asset
        self.plant = plant_name
        self.kpi = kpi_name

        if upper_threshold is None:
            upper_threshold = math.inf

        if lower_threshold is None:
            lower_threshold = -math.inf

        self.upper = upper_threshold
        self.lower = lower_threshold


class Contact:
    def __init__(self, name, email, phone_no, *args):
        self.name = name
        self.email = email
        self.phone_no = phone_no


def get_kpi_data_uri(plant, asset, kpi):
    return f"/api/plant/{plant}/asset/{asset}/kpi/{kpi}/data/"


def get_tracked_assets_and_contacts():
    sheets = Sheets.from_files("credentials.json")
    sheet = sheets[SHEET_NAME]
    thresholds = sheet.sheets[0]
    contacts = sheet.sheets[1]

    raw_thresholds = thresholds.values(False)[1:]
    thresholds = list()
    for thr in raw_thresholds:
        try:
            thresholds.append(AlertObject(*thr))
        except TypeError:
            logger.warning("A threshold row had insufficient information")
            pass

    raw_contacts = contacts.values(False)[1:]
    contacts = list()
    for cont in raw_contacts:
        try:
            contacts.append(Contact(*cont))
        except TypeError:
            logger.warning("A contact row had insufficient information")
            pass

    return thresholds, contacts


def send_email_alerts(contacts, watch, value):
    session = smtplib.SMTP('smtp.gmail.com', 587)
    session.starttls()
    session.login(EMAIL_ADDRESS, PASSWORD)
    for contact in contacts:
        msg = EmailMessage()
        msg.set_content(f"""
        This email is to alert you that a KPI has surpassed
        a given threshold.
        
        Plant: {watch.plant}
        Asset: {watch.ro_name}
        KPI:   {watch.kpi}
        Value: {value}
        """)
        msg['Subject'] = f"Plutoshift alert for {watch.ro_name}"
        msg['From'] = "alerts@plutoshift.com"
        msg['To'] = contact.email
        logging.info(f"Sending email to {contact.email}")
        try:
            session.send_message(msg)
        except Exception as e:
            logger.warning(e)
    session.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("email", type=str,
                        help="Your plutoshift email address")
    parser.add_argument("-p", "--password", type=str,
                        help="Your plutoshift password (not recommended, "
                             "allow script to prompt you for your password")
    args = parser.parse_args()

    email = args.email
    if args.password:
        password = args.password
    else:
        password = getpass("Please enter your plutoshift password:")

    time.sleep(SLEEP_TIME)
    client = PlutoClient(email, password, 'abinbev')

    watches, contacts = get_tracked_assets_and_contacts()
    for watch in watches:
        data = client.get(f"{get_kpi_data_uri(watch.plant, watch.ro_name, watch.kpi)}"
                          f"?time_start={DATA_START}").json()
        data = data['value']
        if data > watch.upper or data < watch.lower:
            logger.info(f"Alert triggered for {watch.ro_name}, data: {data}")
            send_email_alerts(contacts, watch, data)
