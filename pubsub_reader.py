import xmpp
import sys
import os
import time
import pubsubclient
from pubsubclient import Node
import lxml.etree as etree
from random import Random
import string
from lxml.etree import ElementTree, Element, SubElement
import pygtk
import gtk
import gobject
#import webkit
import feedparser
from StringIO import StringIO
from kiwi.ui.objectlist import Column, ObjectTree, ObjectList

class LeftRow:
    def __init__(self, name, count, unread):
        self.name = name
        self.count = count
        self.unread = unread

class FoundRow:
	def __init__(self, name, node):
		self.name = name
		self.node = node

class Display:

	def __init__(self):
		# Make a connection (currently hard coded to my testing server)
		self.jid = 'test2@localhost'
		self.password = 'test'
		self.client = pubsubclient.PubSubClient(self.jid, self.password)
		self.draw_window()

	def draw_window(self):
		# Display related things
		# Make a window and split it into sections
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.hpaned = gtk.HPaned()
		self.window.add(self.hpaned)
		self.right_vpaned = gtk.VPaned()
		self.hpaned.pack2(self.right_vpaned)
		self.left_vbox = gtk.VBox()
		self.hpaned.pack1(self.left_vbox)

		# Make a Kiwi ObjectList with columns "name" and "count" for
		# subscription names and the
		name_column = Column('name', 'Name')
		name_column.expand = True
		unread_column = Column('unread', 'Unread')
		count_column = Column('count', 'Total')
		self.node_list = ObjectList([name_column, unread_column, count_column])
		self.left_vbox.pack_start(self.node_list)

		self.add_button = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_button.set_label("New Subscription")
		self.add_button.connect("released", self.add_released)
		self.left_vbox.pack_end(self.add_button, expand=False)

		title_column = Column('title')
		author_column = Column('author')
		date_column = Column('date')
		title_column.expand = True
		self.entry_list = ObjectList([title_column, author_column, date_column])
		self.right_vpaned.pack1(self.entry_list)

		self.webscroll = gtk.ScrolledWindow()
		#self.webview = webkit.WebView()
		#self.webscroll.add(self.webview)
		self.right_vpaned.pack2(self.webscroll)

		self.window.show_all()

	def disable_subscribe_button(self, args):
		self.add_window['add_button'].set_sensitive(False)

	def subscribe_to_node(self, args):
		#self.pubsub_client
		self.add_window['node_list'].get_selected().subscribe(self.client, self.jid)
		#self.client.subscribe_to_a_node(self.add_window['location_entry'].get_text(), selected.node, return_function=self.subscription_finished)

	def subscription_finished(self, reply):
		print 'Reply received"'
		if reply.find(".//error") is not None:
			print "Error subscribing"
		elif reply.find(".//result") is not None:
			print "Subscription successful!"
			self.add_window['window'].destroy()
			self.node_list.append(LeftRow("lol", 0, 0))

	def add_released(self, args):
		self.add_window = {}

		# Make the Add Node window
		self.add_window['window'] = gtk.Window()
		self.add_window['window'].set_title("Add New Subscription")

		# Split it vertically
		self.add_window['vbox'] = gtk.VBox()
		self.add_window['window'].add(self.add_window['vbox'])

		# Split the top horizontally
		self.add_window['top_hbox'] = gtk.HBox()
		self.add_window['vbox'].pack_start(self.add_window['top_hbox'], expand=False)

		# Add the "Location:" label to the top
		self.add_window['location_label'] = gtk.Label("Location: ")
		self.add_window['top_hbox'].pack_start(self.add_window['location_label'], expand=False)

		# Add the "Find" button to the top
		self.add_window['find_button'] = gtk.Button(label="Find", stock=gtk.STOCK_FIND)
		self.add_window['find_button'].connect("released", self.find_new_nodes)
		self.add_window['top_hbox'].pack_end(self.add_window['find_button'], expand=False)

		# Add the location entry box in between
		self.add_window['location_entry'] = gtk.Entry()
		self.add_window['top_hbox'].pack_end(self.add_window['location_entry'], expand=True)

		self.add_window['bottom_hbox'] = gtk.HBox()
		self.add_window['vbox'].pack_end(self.add_window['bottom_hbox'], expand=False)

		self.add_window['find_progress'] = gtk.ProgressBar()
		self.add_window['bottom_hbox'].pack_end(self.add_window['find_progress'], expand=True)

		self.add_window['add_button'] = gtk.Button(label="Subscribe", stock=gtk.STOCK_ADD)
		self.add_window['add_button'].set_label("Subscribe")
		## FIXME: The Subscribe button should be insensitive to start
		## with, then activate when a node is selected. Need Kiwi docs
		## to do this
		#self.add_window['add_button'].set_sensitive(False)
		self.add_window['add_button'].connect("released", self.subscribe_to_node)
		self.add_window['bottom_hbox'].pack_end(self.add_window['add_button'], expand=False)

		self.add_window['name_column'] = Column('name', 'Name')
		self.add_window['location_column'] = Column('name', 'Location')
		self.add_window['name_column'].expand = True
		self.add_window['location_column'].expand = True
		self.add_window['node_list'] = ObjectList([self.add_window['name_column'], self.add_window['location_column']])
		self.add_window['vbox'].pack_end(self.add_window['node_list'], expand=True, fill=True)

		self.add_window['window'].show_all()

	def pulse_find_progress(self):
		time.sleep(0.05)
		self.add_window['find_progress'].pulse()
		return self.finding

	def find_new_nodes(self, arg):
		self.add_window["entered_server"] = pubsubclient.Server(name=self.add_window['location_entry'].get_text())
		self.client.get_nodes(self.add_window["entered_server"], None, return_function=self.found_new_nodes)
		#self.client.entity_discover_nodes(self.add_window['location_entry'].get_text(), return_function=self.found_new_nodes)
		self.finding = True
		gobject.idle_add(self.pulse_find_progress)

	def found_new_nodes(self, reply):
		"""The program waits until this is run. Could be more elegant
		using a signal though"""
		self.finding = False
		if reply == "error":
			self.add_window['find_progress'].set_fraction(0.0)
			self.add_window['find_progress'].set_text('Error finding nodes at ' + self.add_window['location_entry'].get_text())
		else:
			for node in reply:
				self.add_window['node_list'].append(node)
				#self.client.entity_discover_secondary_nodes(self.add_window["entered_server"], node, self.found_new_nodes)
				node.get_sub_nodes(self.client, self.found_new_nodes)
				self.finding = True

		self.add_window['window'].show_all()

	def connect(self):
		connected = self.client.connect()
		if connected == 1:
			print 'Failed to connect, exiting'
			sys.exit(1)
		self.connected = True
		gobject.idle_add(self.idle_process)

	def handle_incoming(self, stanza):
		#os.popen("mkdir -p pages/")
		#while True:
		#	filename = ''.join(Random().sample(string.letters+string.digits, 16))
		#	if filename not in os.listdir("pages"): break
		#page_file = open("pages/" + filename, 'w')
		#page = Element('html')
		#head = SubElement(page, 'head')
		#css_link = SubElement(head, 'link', attrib={"rel":"stylesheet", "type":"text/css", "href":os.getcwd() + "/page_settings/test1/item.css"})
		#body = SubElement(page, 'body')
		#wholediv = SubElement(body, 'div', attrib={'class':'whole'})
		#titlediv = SubElement(wholediv, 'div', attrib={"class":"title"})
		#maindiv = SubElement(wholediv, 'div', attrib={"class":"main"})
		#for event in stanza.xpath("//e:event", namespaces={"e":"http://jabber.org/protocol/pubsub#event"}):
		#	for item_node in event.xpath("//i:items", namespaces={"i":"http://jabber.org/protocol/pubsub#event"}):
		#		title = SubElement(titlediv, 'a')
		#		title.text = "TITLE: " + item_node.get("node")
		#		body_text = SubElement(maindiv, 'a')
		#		body_text.text = "MAIN: " + item_node.get("node")
		#page_file.write(etree.tostring(page))
		#page_file.close()
		#self.webview.open(os.getcwd() + "/pages/" + filename)
		pass

	def process(self):
		"""Handle any pending XMPP events."""
		self.client.process()

	def idle_process(self):
		time.sleep(0.1)
		self.process()
		return self.connected

	def destroy(self, widget, data=None):
		"""Close the program"""
		gtk.main_quit()

	def main(self):
		#gobject.idle_add(self.idle_process)
		self.window.connect("destroy", self.destroy)
		self.client.assign_message_handler(self.handle_incoming)
		gtk.main()

if __name__ == '__main__':
	display = Display()
	#display.webview.open(os.getcwd() + "/start.html")
	display.connect()
	#display.client.subscribe_to_a_node('pubsub.localhost', '/home')
	#display.populate('pubsub.localhost')
	display.main()
