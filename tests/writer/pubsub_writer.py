import xmpp
import sys
import os
import time
import pubsubclient
import simplexml
import lxml.etree as etree
from random import Random
import string
from lxml.etree import ElementTree, Element, SubElement
import pygtk
import gtk
import gobject
import webkit
import feedparser
from StringIO import StringIO
from kiwi.ui.objectlist import Column, ObjectTree, ObjectList

class Writer:

	def __init__(self):
		self.client = pubsubclient.PubSubClient("test2@localhost", "test")
		self.client.connect()

		self.window = gtk.Window()
		self.window.set_title("PubSub Writer")
		self.window.connect("destroy", self.destroy)
		self.vbox = gtk.VBox()
		self.window.add(self.vbox)
		self.publish_button = gtk.Button(label="Publish")
		self.publish_button.connect("released", self.publish)
		self.vbox.pack_end(self.publish_button)
		self.entry_box = gtk.TextView()
		self.vbox.pack_start(self.entry_box)

	def destroy(self, args):
		gtk.main_quit()

	def main(self):
		self.window.show_all()
		gtk.main()

	def publish(self, args):
		text = self.entry_box.get_buffer().get_text(self.entry_box.get_buffer().get_start_iter(), self.entry_box.get_buffer().get_end_iter())
		valid_text = simplexml.XMLescape(text)
		print valid_text

if __name__ == '__main__':
	writer = Writer()
	writer.main()
	writer.client.entity_request_leaf_node("pubsub.localhost", "heh")
