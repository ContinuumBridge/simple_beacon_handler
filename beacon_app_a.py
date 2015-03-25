#!/usr/bin/env python
# beacon_app_a.py
"""
Copyright (c) 2015 ContinuumBridge Limited
"""

OUT_OF_RANGE_TIME =          10  # If not heard from a beacon for this time, consider it has gone out of range

# Default values:
config = {
          "beacons": [{"name": "No Name",
                       "uuid": ""
                      }
                     ],
          "touch_threshold": 15.0,
          "near_far_threshold": -15.0
}

import sys
import os.path
import time
import json
from cbcommslib import CbApp
from cbconfig import *

class App(CbApp):
    def __init__(self, argv):
        self.appClass = "control"
        self.state = "stopped"
        self.devices = []
        self.idToName = {} 
        self.knownBeacons = []
        self.beaconState = {}
        self.lastSeen = {}
        self.lastReportTime = time.time()
        # Super-class init must be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def reportBeacon(self, name, state):
        # Node doesn't like being bombarded with manager messages
        now = time.time()
        if now -1 > self.lastReportTime:
            msg = {"id": self.id,
                   "status": "user_message",
                   "body": name + " " + state
                  }
            self.sendManagerMessage(msg)
            self.lastReportTime = now 

    def onAdaptorService(self, message):
        #self.cbLog("debug", "onAdaptorService, message: " + str(message))
        for p in message["service"]:
            if p["characteristic"] == "btle_beacon":
                req = {"id": self.id,
                       "request": "service",
                       "service": [
                                   {"characteristic": "btle_beacon",
                                    "interval": 1.0
                                   }
                                  ]
                      }
                self.sendMessage(req, message["id"])

    def onAdaptorData(self, message):
        #self.cbLog("debug", "onAdaptorData, message: " + str(message))
        if True:
        #try:
            if message["characteristic"] == "btle_beacon":
                for b in config["beacons"]:
                    prevState = self.beaconState[b["uuid"]]
                    if message["data"]["uuid"] == b["uuid"]:
                        #self.cbLog("info", "Found " + b["name"] + ", rx power: " + str(message["data"]["rx_power"]))
                        if int(message["data"]["rx_power"]) > int(message["data"]["reference_power"]) + config["touch_threshold"]:
                            self.beaconState[b["uuid"]] = "touched in"
                            self.lastSeen[b["uuid"]] = message["timeStamp"]
                        elif int(message["data"]["rx_power"]) > int(message["data"]["reference_power"]) + config["near_far_threshold"]:
                            self.beaconState[b["uuid"]] = "very near"
                            self.lastSeen[b["uuid"]] = message["timeStamp"]
                        else:
                            self.beaconState[b["uuid"]] = "in range"
                            self.lastSeen[b["uuid"]] = message["timeStamp"]
                    if time.time() - self.lastSeen[b["uuid"]] > OUT_OF_RANGE_TIME:
                        self.beaconState[b["uuid"]] = "not in range"
                    if self.beaconState[b["uuid"]] != prevState:
                        self.cbLog("info", b["name"] + " " + self.beaconState[b["uuid"]] + " (" + str(message["data"]["rx_power"]) + " dBm)")
                        self.reportBeacon(b["name"], self.beaconState[b["uuid"]])
                found = False
                for b in self.knownBeacons:
                    if message["data"]["uuid"] == b:
                        found = True
                        break
                if not found:
                    self.knownBeacons.append(message["data"]["uuid"])
                    self.cbLog("info", "New beacon (or other BTLE device, address: " + message["data"]["address"] + ", UUID: " \
                        + message["data"]["uuid"] + ", reference power: " + str(message["data"]["reference_power"]) )
        #except Exception as ex:
        #    self.cbLog("warning", "onAdaptorData, problem with received message")
        #    self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))

    def onConfigureMessage(self, managerConfig):
        global config
        configFile = CB_CONFIG_DIR + "simple_beacon_app.config"
        try:
            with open(configFile, 'r') as f:
                newConfig = json.load(f)
                self.cbLog("debug", "Read simple_beacon_app.config")
                config.update(newConfig)
        except Exception as ex:
            self.cbLog("warning", "simple_beacon_app.config does not exist or file is corrupt")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))
        for c in config:
            if c.lower in ("true", "t", "1"):
                config[c] = True
            elif c.lower in ("false", "f", "0"):
                config[c] = False
        self.cbLog("debug", "Config: " + str(config))
        now = time.time()
        for b in config["beacons"]:
            self.beaconState[b["uuid"]] = "not in range"
            self.lastSeen[b["uuid"]] = now
        for adaptor in managerConfig["adaptors"]:
            adtID = adaptor["id"]
            if adtID not in self.devices:
                # Because managerConfigure may be re-called if devices are added
                name = adaptor["name"]
                friendly_name = adaptor["friendly_name"]
                self.idToName[adtID] = friendly_name.replace(" ", "_")
                self.devices.append(adtID)
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
