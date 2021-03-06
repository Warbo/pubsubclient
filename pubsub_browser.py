import time
import pubsubclient
from pubsubclient import Node, Server, JID
import pygtk
import gtk
import gobject
from kiwi.ui.objectlist import Column, ObjectTree, ObjectList

class Window(object):
	"""This is the browser application."""

	def __init__(self):
		## FIXME: The GUI should appear straight away, connecting should
		## happen after!
		# Set up the main window
		self.window = gtk.Window()
		self.window.set_title("PubSub Browser")
		self.window.set_default_size(400, 400)
		self.window.connect("destroy", self.quit)

		# Divide it vertically
		self.vbox = gtk.VBox()
		self.window.add(self.vbox)

		# This holds the location entry and the Get button
		self.top_box = gtk.HBox()
		self.vbox.pack_start(self.top_box, expand=False)

		self.location_label = gtk.Label("Server:")
		self.top_box.pack_start(self.location_label, expand=False)

		# This is where the server location is given
		self.location_entry = gtk.Entry()
		self.top_box.pack_start(self.location_entry)

		# This button run get_button_released to fetch the server's nodes
		self.get_button = gtk.Button(label="Get")
		self.get_button.connect("released", self.get_button_released)
		self.top_box.pack_end(self.get_button, expand=False)

		# Draw the tree using Kiwi, since plain GTK is a pain :P

		# The attribute is the data, ie. a Column looking for attribute
		# "foo", when appended by an object bar, will show bar.foo

		# We can put multiple things into a column (eg. an icon and a
		# label) by making 2 columns and passing the first to the second
		self.tree_columns = [\
			Column(attribute='icon', title='Nodes', use_stock=True, \
			justify=gtk.JUSTIFY_LEFT, icon_size=gtk.ICON_SIZE_MENU), \
			Column(attribute='name', justify=gtk.JUSTIFY_LEFT, column='icon')]
		self.tree_columns[0].expand = False
		self.tree_columns[1].expand = False
		self.tree_view = ObjectTree(self.tree_columns)
		self.tree_view.connect("selection-changed", self.selection_changed)
		self.vbox.pack_start(self.tree_view)

		# This holds the Add button and the Delete button
		self.bottom_box = gtk.HBox()
		self.vbox.pack_end(self.bottom_box, expand=False)

		# Make the Delete button, which runs the delete_button_released method
		self.delete_button = gtk.Button(stock=gtk.STOCK_REMOVE)
		try:
			# Attempt to change the label of the stock button
			delete_label = self.delete_button.get_children()[0]
			delete_label = delete_label.get_children()[0].get_children()[1]
			delete_label = delete_label.set_label("Delete Selection")
		except:
			# If it fails then just go back to the default
			self.delete_button = gtk.Button(stock=gtk.STOCK_REMOVE)
		self.delete_button.connect("released", self.delete_button_released)
		self.delete_button.set_sensitive(False)
		self.bottom_box.pack_start(self.delete_button, expand=True)

		# Make the Properties button, which runs the properties_button_released method
		self.properties_button = gtk.Button(stock=gtk.STOCK_PROPERTIES)
		try:
			# Attempt to change the label of the stock button
			properties_label = self.properties_button.get_children()[0]
			properties_label = properties_label.get_children()[0].get_children()[1]
			properties_label = properties_label.set_label("Node Properties...")
		except:
			# If it fails then just go back to the default
			self.properties_button = gtk.Button(stock=gtk.STOCK_PROPERTIES)
		self.properties_button.connect("released", self.properties_button_released)
		self.properties_button.set_sensitive(False)
		self.bottom_box.pack_start(self.properties_button, expand=True)

		# Make the Add button, which runs the add_button_released method
		self.add_button = gtk.Button(stock=gtk.STOCK_ADD)
		try:
			# Attempt to change the label of the stock button
			add_label = self.add_button.get_children()[0]
			add_label = add_label.get_children()[0].get_children()[1]
			add_label = add_label.set_label("Add Child...")
		except:
			# If it fails then just go back to the default
			self.add_button = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_button.connect("released", self.add_button_released)
		self.add_button.set_sensitive(False)
		self.bottom_box.pack_end(self.add_button, expand=True)

		# This handles our XMPP connection. Feel free to change the JID
		# and password
		self.client = pubsubclient.PubSubClient("test1@localhost", "test")

		# Using the tree to store everything seems to have a few
		# glitches, so we use a regular list as our definitive memory
		self.known = []

	def selection_changed(self, list, object):
		self.add_button.set_sensitive(True)
		if type(object) == type(Node()):
			self.delete_button.set_sensitive(True)
			self.properties_button.set_sensitive(True)
		elif type(object) == type(Server()):
			self.delete_button.set_sensitive(False)
			self.properties_button.set_sensitive(False)

	def get_button_released(self, arg):
		"""This is run when the Get button is pressed. It adds the given
		server to the tree and runs get_nodes with that server."""
		listed_server = False		# Assume this server is not listed
		# Check every row of the tree to see if it matches given server
		for known_server in self.tree_view:
			if type(known_server) == type(Server()) and \
				self.location_entry.get_text() == str(known_server):
				listed_server = True		# True if server is listed
		# If we didn't find the server in the tree then add it
		if not listed_server:
			server = Server(name=self.location_entry.get_text())
			server.icon = gtk.STOCK_NETWORK
			self.tree_view.append(None, server)
			self.known.append(server)
		# Get the PubSub nodes on this server
		self.client.get_nodes(self.location_entry.get_text(), None, return_function=self.handle_incoming)

	def handle_incoming(self, nodes):
		# Go through each new node
		for node in nodes:
			# Assume we do not already know about this node
			node_is_known = False
			# Go through each node that we know about
			for known_entry in self.known:
				# See if this node is the same as the known node being checked
				if known_entry.name == node.name:	## FIXME: Needs to check server
					node_is_known = True
			if not node_is_known:
				parent = None
				for known_entry in self.known:
					if known_entry.name == node.parent.name:		## FIXME: Needs to check server
						parent = known_entry

				self.known.append(node)
				self.tree_view.append(parent, node)

				node.get_information(self.client, self.handle_information)

			node.get_sub_nodes(self.client, self.handle_incoming)

	def handle_information(self, node):
		known = False
		if node.type == 'leaf':
			if node.name is not None and node.server is not None:
				for known_entry in self.known:
					if known_entry.name == node.name:
						known_entry.set_type('leaf')
						known_entry.icon = gtk.STOCK_FILE
		elif node.type == 'collection':
			if node.name is not None and node.server is not None:
				for known_entry in self.known:
					if known_entry.name == node.name and known_entry.server == node.server:
						known_entry.set_type('collection')
						known_entry.icon = gtk.STOCK_DIRECTORY
			node.get_sub_nodes(self.client, self.handle_incoming)

	def handle_node_creation(self, return_value):
		if return_value == 0:
			self.tree_view.get_selected().get_sub_nodes(self.client, self.handle_incoming)
		else:
			print return_value

	def delete_button_released(self, args):
		to_delete = self.tree_view.get_selected()
		if type(to_delete) == type(Node()):
			self.client.delete_a_node(to_delete.server, str(to_delete), return_function=self.handle_deleted)

	def handle_deleted(self, return_value):
		if return_value == 0:
			deleted = self.tree_view.get_selected()
			self.tree_view.remove(deleted)
			self.known.remove(deleted)
		else:
			print return_value

	def add_button_released(self, args):
		self.add_window = {}
		self.add_window["parent"] = self.tree_view.get_selected()
		self.add_window["window"] = gtk.Window()
		self.add_window["window"].set_title("Add new node to " + self.add_window["parent"].name)
		self.add_window["vbox"] = gtk.VBox()
		self.add_window["window"].add(self.add_window["vbox"])

		self.add_window["top_box"] = gtk.HBox()
		self.add_window["vbox"].pack_start(self.add_window["top_box"], expand=False)
		self.add_window["name_label"] = gtk.Label("Name:")
		self.add_window["name_entry"] = gtk.Entry()
		self.add_window["top_box"].pack_start(self.add_window["name_label"], expand=False)
		self.add_window["top_box"].pack_end(self.add_window["name_entry"], expand=True)

		self.add_window["bottom_box"] = gtk.HBox()
		self.add_window["vbox"].pack_end(self.add_window["bottom_box"], expand=False)
		self.add_window["add_button"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_window["add_button"].connect("released", self.add_add_released)
		self.add_window["bottom_box"].pack_end(self.add_window["add_button"], expand=False)

		self.add_window["middle_box"] = gtk.HBox()
		self.add_window["vbox"].pack_end(self.add_window["middle_box"], expand=False)
		self.add_window["type_label"] = gtk.Label("Type:")
		self.add_window["type_select"] = gtk.combo_box_new_text()
		self.add_window["type_select"].append_text("Leaf")
		self.add_window["type_select"].append_text("Collection")
		self.add_window["middle_box"].pack_start(self.add_window["type_label"], expand=False)
		self.add_window["middle_box"].pack_end(self.add_window["type_select"], expand=True)

		self.add_window["window"].show_all()

	def add_add_released(self, args):
		name = self.add_window["name_entry"].get_text()
		node_type = self.add_window["type_select"].get_active_text()
		parent = self.add_window["parent"]
		self.add_node(name, node_type, parent)
		self.add_window["window"].destroy()
		del(self.add_window)

	def add_node(self, name, node_type, parent):
		"""Request a new child node of parent. For top-level a node
		parent should be a Server. node_type is either "leaf" or
		"collection"."""
		# This half runs if the parent is a Server
		if type(parent) == type(pubsubclient.Server()):
			# Request a top-level leaf node
			if node_type == 'Leaf':
				self.client.get_new_leaf_node(parent, \
					self.add_window["name_entry"].get_text(), None, None, return_function=self.handle_node_creation)
			# Request a top-level collection node
			elif node_type == 'Collection':
				self.client.get_new_collection_node(parent, \
					self.add_window["name_entry"].get_text(), None, None, return_function=self.handle_node_creation)

		# This half runs if the parent is a Node
		elif type(parent) == type(pubsubclient.Node()):
			# Request a child leaf node
			if node_type == 'Leaf':
				self.client.get_new_leaf_node(parent.server, \
					self.add_window["name_entry"].get_text(), parent, None, return_function=self.handle_node_creation)
			# Request a child collection node
			elif node_type == 'Collection':
				self.client.get_new_collection_node(parent.server, \
					self.add_window["name_entry"].get_text(), parent, None, return_function=self.handle_node_creation)

	def properties_button_released(self, args):
		## FIXME: This should allow multiple properties windows to be open at once
		# Setup a window containing a notebook
		self.properties_window = {}
		self.properties_window["node"] = self.tree_view.get_selected()
		self.properties_window["window"] = gtk.Window()
		self.properties_window["window"].set_title("Properties of " + str(self.properties_window["node"]))
		self.properties_window["window"].set_default_size(350, 450)
		self.properties_window["notebook"] = gtk.Notebook()
		self.properties_window["window"].add(self.properties_window["notebook"])

		# Add the Metadata page
		self.properties_window["metadata_page"] = gtk.VBox()
		self.properties_window["metadata_label"] = gtk.Label("Metadata")
		self.properties_window["notebook"].append_page(self.properties_window["metadata_page"], tab_label=self.properties_window["metadata_label"])

		# Add the Affiliations page
		self.properties_window["affiliations_page"] = gtk.VBox()
		self.properties_window["affiliations_label"] = gtk.Label("Affiliations")
		self.properties_window["notebook"].append_page(self.properties_window["affiliations_page"], tab_label=self.properties_window["affiliations_label"])

		node = self.tree_view.get_selected()
		node.get_information(self.client, self.information_received)
		node.request_all_affiliated_entities(self.client, return_function=self.properties_received)

	def information_received(self, info_dict):
		# Generate the contents of the Metadata page
		## FIXME: It would be awesome if this were generated automatically from what is found :)
		# The Name entry
		self.properties_window["name_box"] = gtk.HBox()
		self.properties_window["metadata_page"].pack_start(self.properties_window["name_box"], expand=False)
		self.properties_window["name_label"] = gtk.Label("Name:")
		self.properties_window["name_box"].pack_start(self.properties_window["name_label"], expand=False)
		self.properties_window["name_entry"] = gtk.Entry()
		self.properties_window["name_entry"].set_text(str(self.properties_window["node"]))		# Default to Node's name
		self.properties_window["name_box"].pack_start(self.properties_window["name_entry"], expand=True)
		self.properties_window["name_set"] = gtk.Button(label="Set")
		self.properties_window["name_set"].connect("released", self.set_name)
		self.properties_window["name_box"].pack_end(self.properties_window["name_set"], expand=False)

		# The Title entry
		## FIXME: This should default to the node's title
		self.properties_window["title_box"] = gtk.HBox()
		self.properties_window["metadata_page"].pack_start(self.properties_window["title_box"], expand=False)
		self.properties_window["title_label"] = gtk.Label("Title:")
		self.properties_window["title_box"].pack_start(self.properties_window["title_label"], expand=False)
		self.properties_window["title_entry"] = gtk.Entry()
		self.properties_window["title_box"].pack_start(self.properties_window["title_entry"], expand=True)
		self.properties_window["title_set"] = gtk.Button(label="Set")
		self.properties_window["title_set"].connect("released", self.set_title)
		self.properties_window["title_box"].pack_end(self.properties_window["title_set"], expand=False)

	def properties_received(self, affiliation_dictionary):
		# Add a warning about affiliation status
		self.properties_window["warning_label"] = gtk.Label("Note that a Jabber ID can only be in one state at a time. Adding a Jabber ID to a category will remove it from the others. There must always be at least one owner.")
		self.properties_window["warning_label"].set_line_wrap(True)
		self.properties_window["affiliations_page"].pack_start(self.properties_window["warning_label"], expand=False)

		# Owners frame
		self.properties_window["owners_frame"] = gtk.Frame("Owners")
		self.properties_window["affiliations_page"].pack_start(self.properties_window["owners_frame"], expand=True)
		self.properties_window["owners_box"] = gtk.HBox()
		self.properties_window["owners_frame"].add(self.properties_window["owners_box"])

		# Owners list
		self.properties_window["owners_column"] = Column(attribute="name", title="Jabber ID")
		self.properties_window["owners"] = ObjectList([self.properties_window["owners_column"]])
		self.properties_window["owners_box"].pack_start(self.properties_window["owners"], expand=True)

		# Add Owner button
		self.properties_window["owners_buttons"] = gtk.VBox()
		self.properties_window["owners_box"].pack_end(self.properties_window["owners_buttons"], expand=False)
		self.properties_window["add_owner"] = gtk.Button(stock=gtk.STOCK_ADD)
		try:
			# Attempt to change the label of the stock button
			label = self.properties_window["add_owner"].get_children()[0]
			label = label.get_children()[0].get_children()[1]
			label = label.set_label("Add...")
		except:
			# If it fails then just go back to the default
			self.properties_window["add_owner"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.properties_window["add_owner"].connect("released", self.add_owner)
		self.properties_window["owners_buttons"].pack_start(self.properties_window["add_owner"], expand=False)

		# Remove Owner button
		self.properties_window["remove_owner"] = gtk.Button(stock=gtk.STOCK_REMOVE)
		self.properties_window["remove_owner"].connect("released", self.remove_owner)
		self.properties_window["owners_buttons"].pack_end(self.properties_window["remove_owner"], expand=False)

		# Publishers frame
		self.properties_window["publishers_frame"] = gtk.Frame("Publishers")
		self.properties_window["affiliations_page"].pack_start(self.properties_window["publishers_frame"], expand=True)
		self.properties_window["publishers_box"] = gtk.HBox()
		self.properties_window["publishers_frame"].add(self.properties_window["publishers_box"])

		# Add Publisher button
		self.properties_window["publishers_buttons"] = gtk.VBox()
		self.properties_window["publishers_box"].pack_end(self.properties_window["publishers_buttons"], expand=False)
		self.properties_window["add_publisher"] = gtk.Button(stock=gtk.STOCK_ADD)
		try:
			# Attempt to change the label of the stock button
			label = self.properties_window["add_publisher"].get_children()[0]
			label = label.get_children()[0].get_children()[1]
			label = label.set_label("Add...")
		except:
			# If it fails then just go back to the default
			self.properties_window["add_publisher"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.properties_window["add_publisher"].connect("released", self.add_publisher)
		self.properties_window["publishers_buttons"].pack_start(self.properties_window["add_publisher"], expand=False)

		# Remove Publisher button
		self.properties_window["remove_publisher"] = gtk.Button(stock=gtk.STOCK_REMOVE)
		self.properties_window["remove_publisher"].connect("released", self.remove_publisher)
		self.properties_window["publishers_buttons"].pack_end(self.properties_window["remove_publisher"], expand=False)

		# Publishers list
		self.properties_window["publishers_column"] = Column(attribute="name", title="Jabber ID")
		self.properties_window["publishers"] = ObjectList([self.properties_window["publishers_column"]])
		self.properties_window["publishers_box"].pack_start(self.properties_window["publishers"], expand=True)

		# Outcasts frame
		self.properties_window["outcasts_frame"] = gtk.Frame("Outcasts")
		self.properties_window["affiliations_page"].pack_start(self.properties_window["outcasts_frame"], expand=True)
		self.properties_window["outcasts_box"] = gtk.HBox()
		self.properties_window["outcasts_frame"].add(self.properties_window["outcasts_box"])

		# Add Outcast button
		self.properties_window["outcasts_buttons"] = gtk.VBox()
		self.properties_window["outcasts_box"].pack_end(self.properties_window["outcasts_buttons"], expand=False)
		self.properties_window["add_outcast"] = gtk.Button(stock=gtk.STOCK_ADD)
		try:
			# Attempt to change the label of the stock button
			label = self.properties_window["add_outcast"].get_children()[0]
			label = label.get_children()[0].get_children()[1]
			label = label.set_label("Add...")
		except:
			# If it fails then just go back to the default
			self.properties_window["add_outcast"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.properties_window["add_outcast"].connect("released", self.add_outcast)
		self.properties_window["outcasts_buttons"].pack_start(self.properties_window["add_outcast"], expand=False)

		# Remove Outcast button
		self.properties_window["remove_outcast"] = gtk.Button(stock=gtk.STOCK_REMOVE)
		self.properties_window["remove_outcast"].connect("released", self.remove_outcast)
		self.properties_window["outcasts_buttons"].pack_end(self.properties_window["remove_outcast"], expand=False)

		# Outcasts list
		self.properties_window["outcasts_column"] = Column(attribute="name", title="Jabber ID")
		self.properties_window["outcasts"] = ObjectList([self.properties_window["outcasts_column"]])
		self.properties_window["outcasts_box"].pack_start(self.properties_window["outcasts"], expand=True)

		self.properties_window["window"].show_all()

		if "owner" in affiliation_dictionary.keys():
			for jid in affiliation_dictionary["owner"]:
				self.properties_window["owners"].append(jid)
		if "publisher" in affiliation_dictionary.keys():
			for jid in affiliation_dictionary["publisher"]:
				self.properties_window["publishers"].append(jid)
		if "outcast" in affiliation_dictionary.keys():
			for jid in affiliation_dictionary["outcast"]:
				self.properties_window["outcasts"].append(jid)

	def set_name(self, args):
		pass

	def set_title(self, args):
		pass

	def add_owner(self, args):
		self.add_owner_window = {}
		self.add_owner_window["window"] = gtk.Window()
		self.add_owner_window["window"].set_title("Add owner to " + str(self.tree_view.get_selected()))
		self.add_owner_window["box"] = gtk.HBox()
		self.add_owner_window["window"].add(self.add_owner_window["box"])
		self.add_owner_window["jid_label"] = gtk.Label("Jabber ID:")
		self.add_owner_window["box"].pack_start(self.add_owner_window["jid_label"], expand=False)
		self.add_owner_window["jid_entry"] = gtk.Entry()
		self.add_owner_window["box"].pack_start(self.add_owner_window["jid_entry"], expand=False)
		self.add_owner_window["add_button"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_owner_window["add_button"].connect("released", self.add_owner_send)
		self.add_owner_window["box"].pack_end(self.add_owner_window["add_button"], expand=False)
		self.add_owner_window["window"].show_all()

	def add_owner_send(self, args):
		self.add_owner_window["jid"] = JID(self.add_owner_window["jid_entry"].get_text())
		self.tree_view.get_selected().modify_affiliations(self.client, {self.add_owner_window["jid"]:"owner"}, self.owner_added)

	def owner_added(self, reply):
		if reply == 0:
			self.properties_window["owners"].append(self.add_owner_window["jid"])
			for jid in self.properties_window["publishers"]:
				if str(jid) == str(self.add_owner_window["jid"]):
					self.properties_window["publishers"].remove(jid)
			for jid in self.properties_window["outcasts"]:
				if str(jid) == str(self.add_owner_window["jid"]):
					self.properties_window["outcasts"].remove(jid)
		else:
			print "Error"
		self.add_owner_window["window"].destroy()
		del self.add_owner_window

	def remove_owner(self, args):
		self.tree_view.get_selected().modify_affiliations(self.client, {self.properties_window["owners"].get_selected():"none"}, self.owner_removed)

	def owner_removed(self, reply):
		if reply == 0:
			self.properties_window["owners"].remove(self.properties_window["owners"].get_selected())
		else:
			print "Error"

	def add_publisher(self, args):
		self.add_publisher_window = {}
		self.add_publisher_window["window"] = gtk.Window()
		self.add_publisher_window["window"].set_title("Add publisher to " + str(self.tree_view.get_selected()))
		self.add_publisher_window["hbox"] = gtk.HBox()
		self.add_publisher_window["window"].add(self.add_publisher_window["hbox"])
		self.add_publisher_window["jid_label"] = gtk.Label("Jabber ID:")
		self.add_publisher_window["hbox"].pack_start(self.add_publisher_window["jid_label"], expand=False)
		self.add_publisher_window["jid_entry"] = gtk.Entry()
		self.add_publisher_window["hbox"].pack_start(self.add_publisher_window["jid_entry"], expand=False)
		self.add_publisher_window["add_button"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_publisher_window["add_button"].connect("released", self.add_publisher_send)
		self.add_publisher_window["hbox"].pack_end(self.add_publisher_window["add_button"], expand=False)
		self.add_publisher_window["window"].show_all()

	def add_publisher_send(self, args):
		self.add_publisher_window["jid"] = JID(self.add_publisher_window["jid_entry"].get_text())
		self.tree_view.get_selected().modify_affiliations(self.client, {self.add_publisher_window["jid"]:"publisher"}, self.publisher_added)

	def publisher_added(self, reply):
		if reply == 0:
			self.properties_window["publishers"].append(self.add_publisher_window["jid"])
			for jid in self.properties_window["owners"]:
				if str(jid) == str(self.add_publisher_window["jid"]):
					self.properties_window["owners"].remove(jid)
			for jid in self.properties_window["outcasts"]:
				if str(jid) == str(self.add_publisher_window["jid"]):
					self.properties_window["outcasts"].remove(jid)
		else:
			print "Error"
		self.add_publisher_window["window"].destroy()
		del self.add_publisher_window

	def remove_publisher(self, args):
		self.tree_view.get_selected().modify_affiliations(self.client, {self.properties_window["publishers"].get_selected():"none"}, self.publisher_removed)

	def publisher_removed(self, reply):
		if reply == 0:
			self.properties_window["publishers"].remove(self.properties_window["publishers"].get_selected())
		else:
			print "Error"

	def add_outcast(self, args):
		self.add_outcast_window = {}
		self.add_outcast_window["window"] = gtk.Window()
		self.add_outcast_window["window"].set_title("Add outcast to " + str(self.tree_view.get_selected()))
		self.add_outcast_window["hbox"] = gtk.HBox()
		self.add_outcast_window["window"].add(self.add_outcast_window["hbox"])
		self.add_outcast_window["jid_label"] = gtk.Label("Jabber ID:")
		self.add_outcast_window["hbox"].pack_start(self.add_outcast_window["jid_label"], expand=False)
		self.add_outcast_window["jid_entry"] = gtk.Entry()
		self.add_outcast_window["hbox"].pack_start(self.add_outcast_window["jid_entry"], expand=False)
		self.add_outcast_window["add_button"] = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_outcast_window["add_button"].connect("released", self.add_outcast_send)
		self.add_outcast_window["hbox"].pack_end(self.add_outcast_window["add_button"], expand=False)
		self.add_outcast_window["window"].show_all()

	def add_outcast_send(self, args):
		self.add_outcast_window["jid"] = JID(self.add_outcast_window["jid_entry"].get_text())
		self.tree_view.get_selected().modify_affiliations(self.client, {self.add_outcast_window["jid"]:"outcast"}, self.outcast_added)

	def outcast_added(self, reply):
		if reply == 0:
			self.properties_window["outcasts"].append(self.add_outcast_window["jid"])
			for jid in self.properties_window["publishers"]:
				if str(jid) == str(self.add_outcast_window["jid"]):
					self.properties_window["publishers"].remove(jid)
			for jid in self.properties_window["owners"]:
				if str(jid) == str(self.add_outcast_window["jid"]):
					self.properties_window["owners"].remove(jid)
		else:
			print "Error"
		self.add_outcast_window["window"].destroy()
		del self.add_outcast_window

	def remove_outcast(self, args):
		self.tree_view.get_selected().modify_affiliations(self.client, {self.properties_window["outcasts"].get_selected():"none"}, self.outcast_removed)

	def outcast_removed(self, reply):
		if reply == 0:
			self.properties_window["outcasts"].remove(self.properties_window["outcasts"].get_selected())
		else:
			print "Error"

	def main(self):
		self.window.show_all()
		self.client.connect()
		#gobject.idle_add(self.idle_process, priority=gobject.PRIORITY_LOW)
		gobject.timeout_add(250, self.idle_process)
		gtk.main()

	def idle_process(self):
		"""A PubSubClient needs its process method run regularly. This
		method can be used to do that in gobject.timeout or idle_add."""
		self.client.process()
		return True

	def quit(self, arg):
		"""Exits the application. Runs when a signal to quit is received."""
		gtk.main_quit()

if __name__ == "__main__":
	main_window = Window()		# Make a browser application

	# This sets a default server, so testing the same server again and
	# again only requires pressing the "Get" button
	main_window.location_entry.set_text("pubsub.localhost")

	main_window.main()		# Run the browser
