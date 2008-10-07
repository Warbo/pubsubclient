import xmpp
import sys
import os
import time
from pubsubclient import PubSubClient, Node, Server, JID
import simplexml
import lxml.etree as etree
from random import Random
import string
from lxml.etree import ElementTree, Element, SubElement
import pygtk
import gtk
import gobject
import feedparser
from StringIO import StringIO
from kiwi.ui.objectlist import Column, ObjectTree, ObjectList

class Writer:

	def __init__(self, node):
		self.client = PubSubClient("test1@localhost", "test")
		self.client.connect()

		self.node = node

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
		gobject.timeout_add(250, self.client.process)
		gtk.main()

	def publish(self, args):
		text = self.entry_box.get_buffer().get_text(self.entry_box.get_buffer().get_start_iter(), self.entry_box.get_buffer().get_end_iter())
		valid_text = simplexml.XMLescape(text)
		all_text = "<item>" + valid_text + "</item>"
		print str(valid_text)
		self.node.publish(self.client, all_text, return_function=self.published)

	def published(self, reply):
		print "Reply received"
		if reply == 0:
			print "Success!"
		else:
			print "Failure :("

if __name__ == '__main__':
	writer = Writer(Node('pubsub.localhost', '/home/localhost/test1/blog/comments'))
	writer.main()
