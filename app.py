import requests
import time
import json
import os
import shutil
from utilsServer import processTrial
import traceback
import logging
import glob
import numpy as np
from utilsAPI import getAPIURL
from utilsAuth import getToken
from utils import getDataDirectory

logging.basicConfig(level=logging.INFO)

API_TOKEN = getToken()
API_URL = getAPIURL()

# if true, will delete entire data directory when finished with a trial
isDocker = True

while True:
    queue_path = "trials/dequeue/"
    try:
        r = requests.get("{}{}".format(API_URL, queue_path),
                         headers = {"Authorization": "Token {}".format(API_TOKEN)})
    except Exception as e:
        traceback.print_exc()
        time.sleep(15)
        continue

    if r.status_code == 404:
        logging.info(".")
        time.sleep(0.5)
        continue
    
    if np.floor(r.status_code/100) == 5: # 5xx codes are server faults
        logging.info("API unresponsive. Status code = {:.0f}.".format(r.status_code))
        time.sleep(5)
        continue

    logging.info(r.text)
    
    trial = r.json()
    trial_url = "{}{}{}/".format(API_URL, "trials/", trial["id"])
    logging.info(trial_url)
    logging.info(trial)
    
    if len(trial["videos"]) == 0:
        error_msg = {}
        error_msg['error_msg'] = 'No videos uploaded. Ensure phones are connected and you have stable internet connection.'
        error_msg['error_msg_dev'] = 'No videos uploaded.'

        r = requests.patch(trial_url, data={"status": "error", "meta": json.dumps(error_msg)},
                         headers = {"Authorization": "Token {}".format(API_TOKEN)})
        continue

    if any([v["video"] is None for v in trial["videos"]]):
        r = requests.patch(trial_url, data={"status": "error"},
                     headers = {"Authorization": "Token {}".format(API_TOKEN)})
        continue

    trial_type = "dynamic"
    if trial["name"] == "calibration":
        trial_type = "calibration"
    if trial["name"] == "neutral":
        trial["name"] = "static"
        trial_type = "static"

    logging.info("processTrial({},{},trial_type={})".format(trial["session"], trial["id"], trial_type))

    try:
        processTrial(trial["session"], trial["id"], trial_type=trial_type, isDocker=isDocker)   
        # note a result needs to be posted for the API to know we finished, but we are posting them 
        # automatically thru procesTrial now
        r = requests.patch(trial_url, data={"status": "done"},
                         headers = {"Authorization": "Token {}".format(API_TOKEN)})
        
        logging.info('0.5s pause if need to restart.')
        time.sleep(0.5)
    except:
        r = requests.patch(trial_url, data={"status": "error"},
                         headers = {"Authorization": "Token {}".format(API_TOKEN)})
        traceback.print_exc()
    
    # Clean data directory
    if isDocker:
        folders = glob.glob(os.path.join(getDataDirectory(isDocker=True),'Data','*'))
        for f in folders:         
            shutil.rmtree(f)
            logging.info('deleting ' + f)
