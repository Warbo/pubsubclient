#!/usr/bin/env python

# Import what we need
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
import xdg.BaseDirectory

class LeftRow:
	"""This is a row on the left-hand pane."""

	def __init__(self, name, count, unread):
		"""name is the name to display, count is the number of items,
		unread is the number of unread items."""
		self.name = name
		self.count = count
		self.unread = unread

class FoundRow:
	"""This is a row in the window which finds and subscribes new nodes."""

	def __init__(self, name, node):
		"""name is the name to display, node is the path of the node on
		the server."""
		self.name = name
		self.node = node

class Display:
	"""This is the main window class."""

	def __init__(self, cache_directory, username, password):
		"""cache_directory is the directory to store downloaded data in,
		username is the JID to login with, password is the password used
		to log in."""
		# Make a connection
		self.jid = username
		self.password = password
		self.client = pubsubclient.PubSubClient(self.jid, self.password)

		# Make the window
		self.draw_window()

	def draw_window(self):
		"""Display related things."""

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

		#self.webscroll = gtk.ScrolledWindow()
		#self.webview = webkit.WebView()
		#self.webscroll.add(self.webview)
		#self.right_vpaned.pack2(self.webscroll)

		self.window.show_all()

	def disable_subscribe_button(self, args):
		"""Makes the subscribe button in the add-new-subscription
		dialogue insensitive."""
		self.add_window['add_button'].set_sensitive(False)

	def subscribe_to_node(self, args):
		"""Subscribes the logged in account to the node selected in the
		add-new-subscription dialogue."""
		self.add_window['node_list'].get_selected().subscribe(self.client, self.jid, return_function=self.subscription_finished)

	def subscription_finished(self, reply):
		"""Handles replies to subscription requests."""
		print 'Reply received"'
		if reply.find(".//error") is not None:
			print "Error subscribing"
		elif reply.find(".//result") is not None:
			print "Subscription successful!"
			# Close the new-subscription dialogue
			self.add_window['window'].destroy()
			# Add the subscribed-to node to the list of subscriptions
			self.node_list.append(LeftRow("test", 0, 0))

	def add_released(self, args):
		"""Run when the "Subscribe" button is pressed."""
		# Make a place to store all of the new GTK stuff
		self.add_window = {}

		# Make the Add Node window and put it in there
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
		## with, then activate when a node is selected.
		#self.add_window['add_button'].set_sensitive(False)
		self.add_window['add_button'].connect("released", self.subscribe_to_node)
		self.add_window['bottom_hbox'].pack_end(self.add_window['add_button'], expand=False)

		# Add the list of found nodes
		self.add_window['name_column'] = Column('name', 'Name')
		self.add_window['location_column'] = Column('name', 'Location')
		self.add_window['name_column'].expand = True
		self.add_window['location_column'].expand = True
		self.add_window['node_list'] = ObjectList([self.add_window['name_column'], self.add_window['location_column']])
		self.add_window['vbox'].pack_end(self.add_window['node_list'], expand=True, fill=True)

		# Display everything
		self.add_window['window'].show_all()

	def pulse_find_progress(self):
		"""Updates the progress bar when finding new nodes."""
		# Sleep here so that we aren't checking for replies constantly
		time.sleep(0.05)
		# Do the pulsing
		self.add_window['find_progress'].pulse()
		# Return whether we're still searching
		return self.finding

	def find_new_nodes(self, arg):
		"""Search for nodes at the server entered in the add-new-subscription window."""
		self.add_window["entered_server"] = pubsubclient.Server(name=self.add_window['location_entry'].get_text())
		self.client.get_nodes(self.add_window["entered_server"], None, return_function=self.found_new_nodes)
		# Remember that we're still on the lookout for nodes
		self.finding = True
		gobject.idle_add(self.pulse_find_progress)

	def found_new_nodes(self, reply):
		"""The program waits until this is run. Could be more elegant
		using a signal though"""
		# We don't need to search any more
		self.finding = False
		# Run the following if we end up with a failure
		if reply == "error":
			# Reset the search progress
			self.add_window['find_progress'].set_fraction(0.0)
			# Tell the user we've failed to find anything due to an error
			self.add_window['find_progress'].set_text('Error finding nodes at ' + self.add_window['location_entry'].get_text())
		# Run the following if we end up with a success
		else:
			# Traverse the nodes we've received
			for node in reply:
				# Add each one to the add-subscription-dialogue's list
				self.add_window['node_list'].append(node)
				# Get any children of the discovered nodes
				node.get_sub_nodes(self.client, self.found_new_nodes)
				# We're now finding for children, so keep up the search
				self.finding = True

		# Display the new window contents
		self.add_window['window'].show_all()

	def connect(self):
		"""Connect the account given during initialisation."""
		# Try to connect
		connected = self.client.connect()
		# Check if we succeeded
		if connected == 1:
			print 'Failed to connect, exiting'
			sys.exit(1)
		self.connected = True
		# Process new messages when there's nothing else to do
		gobject.idle_add(self.idle_process)
		self.client.retrieve_subscriptions(self.add_nodes)

	def add_nodes(self, nodes):
		"""Adds the given nodes to the subscribed list."""
		for node in nodes:
			if node not in self.node_list:
				self.node_list.append(LeftRow(node.name, 0, 0))

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
		"""Check for new messages. Good to run in gobject idle time."""
		# It's a good idea to wait a bit betweeen updates, to stop
		# overworking the machine
		time.sleep(0.1)
		# Do the processing
		self.process()
		# Idle functions stop being called when they return False, in
		# this case when we disconnect
		return self.connected

	def destroy(self, widget, data=None):
		"""Close the program"""
		gtk.main_quit()

	def main(self):
		"""Initialises and starts the GTK main loop."""
		#gobject.idle_add(self.idle_process)
		self.window.connect("destroy", self.destroy)
		self.client.assign_message_handler(self.handle_incoming)
		gtk.main()

if __name__ == '__main__':
	# Check for a writable cache folder, if none is found then make one
	if not 'pubsubclient' in os.listdir(xdg.BaseDirectory.xdg_cache_home):
		try:
			os.mkdir(xdg.BaseDirectory.xdg_cache_home + '/pubsubclient')
		except:
			print 'Error: Could not create cache directory ' + xdg.BaseDirectory.xdg_cache_home + '/pubsubclient'
	# Check for a configuration folder, if none is found then make one
	if not 'pubsubclient' in os.listdir(xdg.BaseDirectory.xdg_config_dirs[0]):
		try:
			os.mkdir(xdg.BaseDirectory.xdg_config_dirs[0] + '/pubsubclient')
		except:
			print 'Error: Could not create config directory ' + xdg.BaseDirectory.xdg_config_dirs[0] + '/pubsubclient'
	# Check for a configuration file, if none is found then make one
	if not 'login' in os.listdir(xdg.BaseDirectory.xdg_config_dirs[0] + '/pubsubclient'):
		id = raw_input("Please enter your Jabber ID: ")
		password = raw_input("Please enter your password: ")
	else:
		try:
			login_file = open(xdg.BaseDirectory.xdg_config_dirs[0] + '/pubsubclient/login', 'r')
			for line in login_file.readlines():
				if line[:4] == 'jid:':
					id = line[4:].strip()
					print "Found jid " + id
				elif line[:5] == 'pass:':
					password = line[5:].strip()
					print "Found password " + password
		except:
			print 'Error: Could not read login details from '+ xdg.BaseDirectory.xdg_config_dirs[0] + '/pubsubclient/login'
			id = raw_input("Please enter your Jabber ID: ")
			password = raw_input("Please enter your password: ")
	# Make a main window
	display = Display(xdg.BaseDirectory.xdg_cache_home + '/pubsubclient', id, password)

	#display.webview.open(os.getcwd() + "/start.html")

	# Log on to XMPP
	display.connect()

	#display.client.subscribe('pubsub.localhost', '/home')
	#display.populate('pubsub.localhost')

	# Run the program
	display.main()
