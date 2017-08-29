# -*- coding: iso-8859-1 -*-
'''
Created on Aug 29, 2017
@initial_author: michaelc
@author: albertKg
'''
import curses
import paho.mqtt.publish as publish    #for publishing to broker
#server has to be started before on host: mosquitto -v -p 5679
#install mosquitto if needed: sudo apt-get install mosquitto
stdscr = curses.initscr()
curses.cbreak()
stdscr.keypad(1)
stdscr.addstr(0,10,"Hit 'q' to Quit")
stdscr.refresh()

key = ''
while key != ord('q'):
    #get key
    key = stdscr.getch()
    #publish key to broker, tokic='s2t', payload, hostname=ip where you started mosquitto, port=port at which mosquitto listens
    publish.single("s2t",str(key),hostname='127.0.0.1', port=5679)
    #publish.single("s2t",str(key),hostname='10.0.2.15', port=5679)

print "END"
curses.endwin()
