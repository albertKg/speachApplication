'''
Created on Aug 29, 2017
@initial_author: michaelc
@author: albertKg
'''

import gtk
import gobject
from motors import Motors
from video import Video
from application import Application


def main():
    gobject.threads_init()
    motors = Motors()
    video = Video()
    app = Application(motors, video)
    gtk.main()
    if video.thread:
        video.thread.quit = True

if __name__ == '__main__':
    main()
