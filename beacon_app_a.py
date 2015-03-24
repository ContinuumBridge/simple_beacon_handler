#!/usr/bin/env python
# beacon_app_a.py
"""
Copyright (c) 2015 ContinuumBridge Limited
"""

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
        # Super-class init must be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

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
        try:
            if message["characteristic"] == "btle_beacon":
                for b in config["beacons"]:
                    if message["data"]["uuid"] == b["uuid"]:
                        #self.cbLog("info", "Found " + b["name"] + ", rx power: " + str(message["data"]["rx_power"]))
                        if int(message["data"]["rx_power"]) > int(message["data"]["reference_power"]) + config["touch_threshold"]:
                            self.cbLog("info", b["name"] + " touched in (" + str(message["data"]["rx_power"]) + " dBm)")
                        elif int(message["data"]["rx_power"]) > int(message["data"]["reference_power"]) + config["near_far_threshold"]:
                            self.cbLog("info", b["name"] + " very near (" + str(message["data"]["rx_power"]) + " dBm)")
                        else:
                            self.cbLog("info", b["name"] + " in range (" + str(message["data"]["rx_power"]) + " dBm)")
                found = False
                for b in self.knownBeacons:
                    if message["data"]["uuid"] == b:
                        found = True
                        break
                if not found:
                    self.knownBeacons.append(message["data"]["uuid"])
                    self.cbLog("info", "New beacon (or other BTLE device, UUID: " + message["data"]["uuid"] + ", reference power: " + str(message["data"]["reference_power"]) )
        except Exception as ex:
            self.cbLog("warning", "onAdaptorData, problem with received message")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))

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
