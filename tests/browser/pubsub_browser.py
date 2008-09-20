import time
import pubsubclient
from pubsubclient import Node, Server
import pygtk
import gtk
import gobject
from kiwi.ui.objectlist import Column, ObjectTree, ObjectList

class Window(object):

	def __init__(self):
		self.window = gtk.Window()
		self.window.set_title("PubSub Browser")
		self.window.connect("destroy", self.quit)
		self.vbox = gtk.VBox()
		self.window.add(self.vbox)
		self.top_box = gtk.HBox()
		self.add_button = gtk.Button(stock=gtk.STOCK_ADD)
		self.add_button.connect("released", self.add_button_released)
		self.vbox.pack_start(self.top_box, expand=False)
		self.top_box.pack_start(self.add_button, expand=False)
		self.location_entry = gtk.Entry()
		self.top_box.pack_start(self.location_entry)
		self.get_button = gtk.Button(label="Get")
		self.get_button.connect("released", self.get_button_released)
		self.top_box.pack_end(self.get_button, expand=False)
		self.tree_columns = [Column(attribute='icon', title='Nodes', use_stock=True, justify=gtk.JUSTIFY_LEFT, icon_size=gtk.ICON_SIZE_MENU), Column(attribute='name', justify=gtk.JUSTIFY_LEFT, column='icon')]
		self.tree_columns[0].expand = False
		self.tree_columns[1].expand = False
		#self.tree_columns[0].cell_data_func = self.tree_columns[0]._cell_data_pixbuf_func
		self.tree_view = ObjectTree(self.tree_columns)

		self.vbox.pack_end(self.tree_view)

		self.client = pubsubclient.PubSubClient("test1@localhost", "test")

		self.known = []

	def get_button_released(self, arg):
		listed_server = False
		for known_server in self.tree_view:
			if type(known_server) == type(Server()) and self.location_entry.get_text() == known_server.name:
				listed_server = True
		if not listed_server:
			server = Server(name=self.location_entry.get_text())
			server.icon = gtk.STOCK_NETWORK
			self.tree_view.append(None, server)
			self.known.append(server)
		self.client.get_nodes_at(self.location_entry.get_text(), None, return_function=self.handle_incoming)

	def handle_incoming(self, nodes):
		print "function started"
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
		type = self.add_window["type_select"].get_active_text()
		parent = self.add_window["parent"]
		self.add_window["window"].destroy()
		del(self.add_window)
		self.add_node(name, type, parent)

	def add_node(self, name, type, parent):
		parent.

	def main(self):
		self.window.show_all()
		self.client.connect()
		#gobject.idle_add(self.idle_process, priority=gobject.PRIORITY_LOW)
		gobject.timeout_add(250, self.idle_process)
		gtk.main()

	def idle_process(self):
		#print "processing"
		self.client.process()
		return True

	def quit(self, arg):
		gtk.main_quit()

if __name__ == "__main__":
	main_window = Window()
	main_window.location_entry.set_text("pubsub.localhost")
	main_window.main()
