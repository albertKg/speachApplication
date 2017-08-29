'''
Created on Aug 29, 2017
@initial_author: michaelc
@author: albertKg
'''

import pygtk
from operator import pos
pygtk.require('2.0')
import gtk
import glib
from motors import Motors, DEFAULT_IP

import paho.mqtt.client as mqtt
import threading

class applicationThread(threading.Thread):
    '''
    A background MQTTthread 
    '''
    def __init__(self,app):
        super(applicationThread, self).__init__()
        self.app = app
        self.client = None

    def run(self):
        print("Start mqtt.Client ")
        self.client = mqtt.Client()
        print("Start mqtt.on_connect ")
        self.client.on_connect = self.on_connectMQTT
        self.client.on_message = self.on_messageMQTT
        
        print("Start client.connect ")
        self.client.connect("localhost", 5679)
        rc = self.client.loop_start()
        print("mqtt.Client.rc: " + str(rc))

        
    def on_connectMQTT(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe("s2t")

    def on_messageMQTT(self, client, userdata, msg):
        intData=int(msg.payload)
        if intData > 255: return
        self.app.dataString += chr(int(msg.payload))
        self.app.receiveData=True
        print("             ON_MESSAGE" + msg.topic + " " + self.app.dataString )

class Application(object):
    def __init__(self, motors, video):
        self.motors = motors
        self.video = video
        self.ip_box = None
        
        self.debug = True
        self.debugBig = True
        self.MIN_ERROR = 1
        self.keystate = {k: False for k in ['Up','Down','Left','Right','a','z','x']}
        self.receiveData=False
        self.commandArray = {
                             'Up':   ['forward','vorward','forvard', 'forwart','vorwart','forvart',],
                             'Down': ['back', 'pack', 'bek', 'pek',],
                             'Left': ['left','levt','lefd','levd', ],
                             'Right':['right', 'rait', 'raid'], 
                             'a': ['camera up',  'cameraup', 'kameraab', 'kameraap'],
                             'z': ['stop', 'stob',], 
                             'x': ['camera down','cameradown', 'kamera down' ,'kameradown' ],}

        print("Start app ")
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title('WiFi Tank Remote')
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(10)

        layout = gtk.VBox(False, 5)

        self.connect_box = self.setup_connection_box()
        layout.add(self.connect_box)

        self.direction_pad = self.setup_direction_pad()
        layout.add(self.direction_pad)

        self.vid_img = self.setup_video_image()
        layout.add(self.vid_img)

        layout.show()
        self.window.add(layout)

        self.motors.connect('connected', self.on_connection_state_change)

        self.window.connect("key-press-event", self.on_key_down)
        self.window.connect("key-release-event", self.on_key_up)
        self.window.set_events(gtk.gdk.KEY_PRESS_MASK  | gtk.gdk.KEY_RELEASE_MASK)

        self.window.show()

        glib.timeout_add(100, self.tick)
        
        print 'Starting application thread'
        self.dataString = ''
        self.guit=False
        self.thread = applicationThread(self)
        self.thread.start()



    def setup_direction_pad(self):
        box = gtk.VBox(False, 0)
        button_config = [
            [
                ('Forward (↑)', ((Motors.LEFT, Motors.FORWARD),
                                 (Motors.RIGHT, Motors.FORWARD)))
            ],
            [
                ('Left (←)', ((Motors.LEFT, Motors.BACK),
                              (Motors.RIGHT, Motors.FORWARD))),
                ('Back (↓)', ((Motors.LEFT, Motors.BACK),
                              (Motors.RIGHT, Motors.BACK))),
                ('Right (→)', ((Motors.LEFT, Motors.FORWARD),
                               (Motors.RIGHT, Motors.BACK)))
            ],
            [
                ('Camera Up (a)', ((Motors.CAMERA, Motors.FORWARD),)),
                ('Stop (x)', ((Motors.LEFT, Motors.STOP),
                              (Motors.RIGHT, Motors.STOP),
                              (Motors.CAMERA, Motors.STOP))),
                ('Camera Down (z)', ((Motors.CAMERA, Motors.BACK),))
            ]
        ]

        for buttons_set in button_config:
            hbox = gtk.HBox(False, 0)
            box.pack_start(hbox, True, True, 0)
            for title, commands in buttons_set:
                inst = gtk.Button(title)
                inst.connect('clicked', self.send_command, commands)
                inst.show()
                hbox.pack_start(inst, True, True, 0)
            hbox.show()

        box.set_sensitive(False)
        box.show()
        return box

    def setup_connection_box(self):
        box = gtk.HBox(False, 0)
        self.ip_box = gtk.Entry(16)
        self.ip_box.set_text(DEFAULT_IP)
        self.ip_box.show()
        box.pack_start(self.ip_box, True, True, 0)

        connect_btn = gtk.Button('Connect')
        connect_btn.connect('clicked', self.on_click_connect)
        connect_btn.show()
        box.pack_start(connect_btn, True, True, 0)

        box.show()
        return box

    def setup_video_image(self):
        img = gtk.Image()
        img.show()
        self.video.widget = img
        return img

    def send_command(self, _, data=None):
        for cmd in data:
            self.motors.command(cmd[0], cmd[1])

    def tick(self):
        if self.receiveData:
            self.receiveData=False 
            if self.findGoodSequence(self.dataString): self.dataString = ''
            
        if self.motors.is_connected:
            left_track = Motors.STOP
            right_track = Motors.STOP
            camera_track = Motors.STOP

            if self.keystate['Up']:
                left_track = Motors.FORWARD if not self.keystate['Left'] else Motors.STOP
                right_track = Motors.FORWARD if not self.keystate['Right'] else Motors.STOP
            elif self.keystate['Down']:
                left_track = Motors.BACK if not self.keystate['Left'] else Motors.STOP
                right_track = Motors.BACK if not self.keystate['Right'] else Motors.STOP
            elif self.keystate['Left']:
                left_track = Motors.BACK
                right_track = Motors.FORWARD
            elif self.keystate['Right']:
                left_track = Motors.FORWARD
                right_track = Motors.BACK

            if self.keystate['a']:
                camera_track = Motors.FORWARD
            elif self.keystate['z']:
                camera_track = Motors.BACK

            self.motors.command(Motors.LEFT, left_track)
            self.motors.command(Motors.RIGHT, right_track)
            self.motors.command(Motors.CAMERA, camera_track)
            self.clearKeystay()
        return True

    def on_key_down(self, widget, data=None):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname in self.keystate.keys():
            self.keystate[keyname] = True

    def on_key_up(self, widget, data=None):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname in self.keystate.keys():
            self.keystate[keyname] = False

    def on_connection_state_change(self, _, connected):
        self.direction_pad.set_sensitive(connected)
        self.connect_box.set_sensitive(not connected)
        # Reset keys just in case
        for k in self.keystate.keys():
            self.keystate[k] = False

    def on_click_connect(self, _, data=None):
        self.motors.init_connection(self.ip_box.get_text())
        self.video.init_connection(self.ip_box.get_text())

    def destroy(self, _, data=None):
        self.thread.client.loop_stop()
        gtk.main_quit()
    
    def findGoodSequence(self,data): 
        
        if self.debug: print  " findGoodSequence: rawDataArray=", repr(data) , ". <- \n"  
        maxPos = -1
        answerWord = None
        key = None
        for keyStr in self.commandArray.keys():
            pos, transformLength, transformWord = self.wordDistance (keyStr, data.lower())
            if pos >= 0 and transformLength <= self.MIN_ERROR :
                if self.debugBig: print  data, "  findGoodSequence: rawDataArray= command inside!", transformWord,"\n"       
                
                if pos > maxPos: 
                    maxPos = pos
                    answerWord = transformWord
                    key=keyStr

       
        if maxPos >= 0:
            if self.debugBig: print  data, "  findGoodSequence: finally", answerWord, key, "\n"   
            self.clearKeystay()
            self.keystate[key]=True
            return True
        
        if self.debug: print  "   findGoodSequence: return False <- \n" 
        return False
    
    def wordDistance (self, keyStr, data):            
        normalAnswer = self.commandArray[keyStr][0]
        
        for transformStr in self.commandArray[keyStr]:
            if transformStr in data:
                diffCount = 0;
                rindexPos = data.rindex(transformStr)
                
                for i in range (len(transformStr)):
                    if transformStr[i] != normalAnswer[i] : 
                        diffCount += 1
                               
                return rindexPos , diffCount, transformStr
            pass
        
        return -1, 0, None
        
    def clearKeystay(self): 
        self.keystate = {k: False for k in ['Up','Down','Left','Right','a','z','x']}
