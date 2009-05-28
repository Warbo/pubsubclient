#    PubSubClient, a Python library for interacting with XMPP PubSub
#    Copyright (C) 2008  Chris Warburton
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

### WARNING: This library is still early in development. Expected changes
### include:
### * Consistent naming of PubSubClient methods
### * Any usage of a server URL should accept a string AND a Server
### * Combine some of PubSubClient's methods into fewer, more generic ones
### * Make some of PubSubClient's methods private after API stabilises
### * Possible new objects: Entity? Affiliate? Option?

import xmpp
import string
from random import Random
from StringIO import StringIO
from lxml.etree import ElementTree, Element, SubElement
import lxml.etree as etree

class PubSubClient(object):

	def __init__(self, jid, password, resource='subscriptions'):
		"""Creates a new PubSubClient. jid can be a string or a JID,
		password and resource are strings."""
		# Store all of the information we need to connect to Jabber
		# The user and server can be deduced from the JabberID
		# FIXME: This is probably really insecure password storage?
		self.password = password
		self.resource = resource
		if type(jid) == type("string"):
			self.jid = JID(jid)
		elif type(jid) == type(JID()):
			self.jid = jid
		self.user = self.jid.getNode()
		self.server = self.jid.getDomain()
		self.connection = xmpp.Client(self.server,debug=[])

		# self.pending uses the stanza id of any requests which are
		# awaiting a response as keys, with assigned values of the
		# predefined functions which should handle these responses.
		# IMPORTANT: The functions are stored in a list since functions
		# cannot be directly stored in dictionaries. Each list contains
		# just one function, ie. {'id1':[function1], 'id2':[function2]}
		# To call a function use self.pending[id][0](stanza)
		self.pending = {}

		# self.callbacks works in a similar way to self.pending, except
		# that it maps stanza ids to functions given by the programmer
		# using the library. These functions are passed to the
		# appropriate handler function from self.pending, and are
		# executed by those functions when they have finished
		# processing the replies
		self.callbacks = {}

		# This stores the stanza ids used for this session, since ids
		# must be unique for their session
		self.used_ids = []

		# Assign a default printing handler for messages
		self.assign_message_handler(self.default_handler)

	def default_handler(self, message):
		print etree.tostring(message)

	def connect(self):
		"""Turn on the connection. Returns 1 for error, 0 for success."""
		# First try connecting to the server
		connection_result = self.connection.connect()
		if not connection_result:
			print "Could not connect to server " + str(self.server)
			return 1
		if connection_result != 'tls':
			print "Warning: Could not use TLS"

		# Then try to log in
		authorisation_result = self.connection.auth(self.user, \
													self.password, \
													self.resource)
		if not authorisation_result:
			print "Could not get authorized. Username/password problem?"
			return 1
		if authorisation_result != 'sasl':
			print "Warning: Could not use SASL"

		# Here we specify which methods to run to process messages and
		# queries
		self.connection.RegisterHandler('message', self.message_handler)
		self.connection.RegisterHandler('iq', self.iq_handler)

		# Tell the network we are online but don't ask for the roster
		self.connection.sendInitPresence(1)

		print "Connected."
		return 0

	def process(self):
		"""This looks for any new messages and passes those it finds to
		the assigned handling method."""
		self.connection.Process()

	def get_jid(self, jid=None, use=False):
		"""This is a convenience method which returns the given JID if
		it is not None, or else returns the object's assigned JID."""
		if jid == None or use == False:
			return str(self.jid)
		else:
			return str(jid)

	def assign_message_handler(self, handler_function):
		"""This causes the function handler_function to run whenever a
		message of type "message" is received."""
		self.message_handler_function = handler_function

	def message_handler(self, connection, message):
		"""Passes incoming stanzas of type "message" to the function
		assigned to handle messages."""
		## FIXME: Doesn't do anything at the moment
		print message.__str__(1)
		message = ElementTree(file=StringIO(message))
		message_root = message.getroot()
		self.message_handler_function(message_root)

	def iq_handler(self, connection, iq):
		"""Looks at every incoming Jabber iq stanza and handles them."""
		# This creates an XML object out of the stanza, making it more
		# manageable
		stanza = ElementTree(file=StringIO(iq))
		# Gets the top-level XML element of the stanza (the 'iq' one)
		stanza_root = stanza.getroot()

		# See if there is a stanza id and if so whether it is in the
		# dictionary of stanzas awaiting replies.
		if 'id' in stanza_root.attrib.keys() and stanza_root.get('id') in self.pending.keys():
			# This stanza must be a reply, therefore run the function
			# which is assigned to handle it
			self.pending[stanza_root.get('id')][0](stanza_root, self.callbacks[stanza_root.get('id')][0])
			# These won't be run again, so collect the garbage
			del(self.pending[stanza_root.get('id')])
			del(self.callbacks[stanza_root.get('id')])

	def send(self, stanza, reply_handler=None, callback=None):
		"""Sends the given stanza through the connection, giving it a
		random stanza id if it doesn't have one or if the current one
		is not unique. Also assigns the optional functions
		'reply_handler' and 'callback' to handle replies to this stanza."""
		# Get the id of this stanza if it has one,
		# or else make a new random one
		if 'id' in stanza.attrib.keys() and stanza.get('id') not in self.used_ids:
			id = stanza.get('id')
		else:
			# Make a random ID which is not already used
			while True:
				id = ''.join(Random().sample(string.digits+string.ascii_letters, 8))
				if id not in self.used_ids: break
			stanza.set('id', id)
		self.used_ids.append(id)
		self.pending[id] = [reply_handler]
		self.callbacks[id] = [callback]
		self.connection.send(etree.tostring(stanza))

	def get_features(self, server, return_function=None, stanza_id=None):		#FIXME IDENTITY NOT HANDLED
		"""Queries server (string or Server) for the XMPP features it
		supports."""
		# This is the kind of XML we want to send
		#<iq type='get' from='us' to='them'>
		#  <query xmlns='http://jabber.org/protocol/disco#info' />
		#</iq>

		# Make it as XML
		contents = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		contents.append(Element('query', attrib={'xmlns':'http://jabber.org/protocol/disco#info'}))

		# This function is run when any replies are received with the
		# same stanza id as a get_features stanza. The
		# stanza argument is the reply stanza which has been received
		def handler(stanza, to_run):
			## FIXME: This handles <feature> but not <identity>
			if to_run is not None:
				# See if the server is not in our server_properties tree
				reply = Element('reply', attrib={'id':stanza.get('id')})
				# If this is an error report then say so
				if stanza.attrib.get('type') == 'error':
					error = SubElement(reply, 'error')
				# If this is a successful reply then handle it
				elif stanza.attrib.get('type') == 'result':
					identities = []
					features = []
					for query in stanza.xpath(".//{http://jabber.org/protocol/disco#info}query"):
						for identity in query.xpath("{http://jabber.org/protocol/disco#info}identity"):
							# Handle identity children
							## FIXME: Doesn't do anything yet
							pass
						for feature in query.xpath("{http://jabber.org/protocol/disco#info}feature"):
							# Handle feature children, adding features to
							# the server's entry in server_properties
							features.append(feature.get('var'))
					to_run(reply)

		# Send the message and set the handler function above to deal with the reply
		self.send(contents, handler, return_function)

	def get_nodes(self, server, node, return_function=None, stanza_id=None):
		"""Queries server (string or Server) for the top-level nodes it
		contains. If node is a string or Node then its child nodes are
		requested instead.

		Upon reply, return_function is called with a list of Nodes which
		were returned."""
		# This is the kind of XML we want to send
		# <iq type='get' from='us' to='them'>
		#  <query xmlns='http://jabber.org/protocol/disco#items'/>
		#</iq>

		# Make it as XML elements
		contents = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		query = SubElement(contents, 'query', attrib={'xmlns':'http://jabber.org/protocol/disco#items'})
		if node is not None:
			query.set('node', node.name)

		# This is run on any replies that are received (identified by
		# their stanza id)
		def handler(stanza, callback):
			#<iq type='result'
			#    from='pubsub.shakespeare.lit'
			#    to='francisco@denmark.lit/barracks'
			#    id='nodes2'>
			#  <query xmlns='http://jabber.org/protocol/disco#items'
			#         node='blogs'>
			#    <item jid='pubsub.shakespeare.lit'
			#          node='princely_musings'/>
			#    <item jid='pubsub.shakespeare.lit'
			#          node='kingly_ravings'/>
			#    <item jid='pubsub.shakespeare.lit'
			#          node='starcrossed_stories'/>
			#    <item jid='pubsub.shakespeare.lit'
			#          node='moorish_meanderings'/>
			#  </query>
			#</iq>
			if callback is not None:
				#reply = Element('reply')
				reply = []
				if stanza.attrib.get('type') == 'error':
					# FIXME: Make this handle errors in a meaningful way
					#error = SubElement(reply, 'error')
					print "Error"
					callback("error")
				elif stanza.attrib.get('type') == 'result':
					# This is run if the request has been successful
					if stanza.find('.//{http://jabber.org/protocol/disco#items}query').get('node') is not None:
						node_parent = Node(name=stanza.find('.//{http://jabber.org/protocol/disco#items}query').get('node'), server=Server(name=stanza.get('from')))
					else:
						node_parent = Server(name=stanza.get('from'))
					# Go through all of the 'item' elements in the stanza
					for item in stanza.findall('.//{http://jabber.org/protocol/disco#items}item'):
						reply.append(Node(name=item.get('node'), jid=item.get('jid'), server=Server(name=stanza.get('from')), parent=node_parent))
				callback(reply)

		self.send(contents, handler, return_function)

	def get_node_information(self, server, node, return_function=None, stanza_id=None):		#FIXME NEEDS MOAR INFO
		"""Queries node (string or Node) on server (string or Server)
		for its metadata."""
		#<iq type='get' from='us' to='server'>
		#  <query xmlns='http://jabber.org/protocol/disco#info' node='node_name'/>
		#</iq>

		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		stanza.append(Element('query', attrib={'xmlns':'http://jabber.org/protocol/disco#info', 'node':str(node)}))

		def handler(stanza, callback):
			#print etree.tostring(stanza)
			## FIXME: Much more information available
			if callback is not None:
				#<iq type='result'
				#    from='pubsub.shakespeare.lit'
				#    to='francisco@denmark.lit/barracks'
				#    id='meta1'>
				#  <query xmlns='http://jabber.org/protocol/disco#info'
				#         node='blogs'>
				#    ...
				#    <identity category='pubsub' type='collection'/>
				#    ...
				#  </query>
				#</iq>
				if stanza.get('type') == 'result':
					node = Node(server=stanza.get('from'), name=stanza.find('{http://jabber.org/protocol/disco#info}query').get('node'))
					#for element in stanza.xpath("//query"):
					for element in stanza.find("{http://jabber.org/protocol/disco#info}query"):
						try:
							if element.get('type') == 'collection':
								node.set_type('collection')
							elif element.get('type') == 'leaf':
								node.set_type('leaf')
						except:
							pass
					callback(node)
				#etree.tostring()

		self.send(stanza, handler, return_function)

	def get_items(self, server, node, return_function=None, stanza_id=None):
		"""Requests the items of node (string or Node) on server (string
		or Server)."""
		#<iq type='get'
		#    from='jid'
		#    to='server'>
		#  <query xmlns='http://jabber.org/protocol/disco#items'
		#         node='node_name'/>
		#</iq>

		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		query = SubElement(stanza, 'query', attrib={'xmlns':'http://jabber.org/protocol/disco#items', 'node':str(node)})

		def handler(stanza, callback):
			#<iq type='result'
			#    from='pubsub.shakespeare.lit'
			#    to='francisco@denmark.lit/barracks'
			#    id='items1'>
			#  <query xmlns='http://jabber.org/protocol/disco#items'
			#         node='princely_musings'>
			#    <item jid='pubsub.shakespeare.lit' name='368866411b877c30064a5f62b917cffe'/>
			#    <item jid='pubsub.shakespeare.lit' name='3300659945416e274474e469a1f0154c'/>
			#    <item jid='pubsub.shakespeare.lit' name='4e30f35051b7b8b42abe083742187228'/>
			#    <item jid='pubsub.shakespeare.lit' name='ae890ac52d0df67ed7cfdf51b644e901'/>
			#  </query>
			#</iq>
			if callback is not None:
				if stanza.get('type') == 'error':
					items = False
				elif stanza.get('type') == 'result':
					# Make an empty list to store discovered items in
					items = []
					# Find every 'item' element
					for item in stanza.findall('.//{http://jabber.org/protocol/disco#items}item'):
						# Add new Items to the items list for each
						items.append(Item(jid=item.get('jid'), name=item.get('name')))
				# Give the items found to the callback function
				callback(items)

		self.send(stanza, handler, return_function)

	def get_subscriptions(self, server, node, return_function=None, stanza_id=None):
		"""Redundant."""
		#<iq type='get' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscriptions/>
		#  </pubsub>
		#</iq>
		self.retrieve_subscriptions(server, node, return_function, stanza_id)

	def get_affiliations(self, server, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Requests all afilliations on server (string or Server)."""
		#<iq type='get' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <affiliations/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		affiliations = SubElement(pubsub, 'affiliations')

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def subscribe(self, server, node, jid=None, return_function=None, stanza_id=None):
		"""Subscribe the current JID to node on server. If supplied, jid
		will be subscribed rather than the logged-in JID.

		return_function is given a single argument. This is False if there
		was an error, or if it was successful it is given a list of
		dictionaries of the form:

		[{'server':server_URL, 'jid':subscribed_jid, 'subid':subscription_ID}, {...}, ...]"""

		#<iq type='set' from='francisco@denmark.lit/barracks' to='pubsub.shakespeare.lit'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscribe node='princely_musings' jid='francisco@denmark.lit'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		subscribe = SubElement(pubsub, 'subscribe', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})

		def handler(stanza, callback):
			#<iq xmlns="jabber:client" to="test2@localhost/subscriptions" from="pubsub.localhost" id="9r4LiyWpTOhI7z0j" type="result">
			#  <pubsub xmlns="http://jabber.org/protocol/pubsub">
			#    <subscription subid="4C1430B5BE841" node="/home" jid="test2@localhost/subscriptions" subscription="subscribed"/>
			#  </pubsub>
			#</iq

			#<iq type='result' from='pubsub.shakespeare.lit' to='francisco@denmark.lit/barracks'>
			#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
			#    <subscription node='princely_musings' jid='francisco@denmark.lit' subid='ba49252aaa4f5d320c24d3766f0bdcade78c78d3' subscription='subscribed'/>
			#  </pubsub>
			#</iq>

			if callback is not None:
				if stanza.get('type') == 'error':
					reply = False
				elif stanza.get('type') == 'result':
					reply = []
					for subscription_element in stanza.xpath(".//subscription"):
						reply.append({'node':subscription_element.get('node'), 'subid':subscription_element.get('subid'), 'server':stanza.get('from'), 'jid':subscription_element.get('jid')}))
				callback(reply)

		self.send(stanza, handler, return_function)

	def unsubscribe(self, server, node, jid=None, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Unsubscribe the given jid (or if not supplied, the currently
		logged-in JID) from node on server.

		No reply handling yet."""		#FIXME: Add description of return_function arguments
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#     <unsubscribe
		#         node='node_name'
		#         jid='jid'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		unsubscribe = SubElement(pubsub, 'unsubscribe', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def get_subscription_options(self, server, node, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Request the subscription options of jid (or if not supplied,
		the currently logged-in JID) for node on server.

		No reply handling yet."""
		#<iq type='get'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <options node='node_name' jid='jid'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		options = SubElement(pubsub, 'options', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def subscription_options_form_submission(self, server, node, options, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		# options is the "x" Element (which should contain all of the SubElements needed)
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <options node='node_name' jid='jid'>
		#        <x xmlns='jabber:x:data' type='submit'>
		#          <field var='FORM_TYPE' type='hidden'>
		#            <value>http://jabber.org/protocol/pubsub#subscribe_options</value>
		#          </field>
		#          <field var='pubsub#deliver'><value>1</value></field>
		#          <field var='pubsub#digest'><value>0</value></field>
		#          <field var='pubsub#include_body'><value>false</value></field>
		#          <field var='pubsub#show-values'>
		#            <value>chat</value>
		#            <value>online</value>
		#            <value>away</value>
		#          </field>
		#        </x>
		#     </options>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		options_stanza = SubElement(pubsub, 'options', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})
		options.append(options)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def subscribe_to_and_configure_a_node(self, server, node, options, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscribe node='node_name' jid='jid'/>
		#    <options>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#subscribe_options</value>
		#        </field>
		#        <field var='pubsub#deliver'><value>1</value></field>
		#        <field var='pubsub#digest'><value>0</value></field>
		#        <field var='pubsub#include_body'><value>false</value></field>
		#        <field var='pubsub#show-values'>
		#          <value>chat</value>
		#          <value>online</value>
		#          <value>away</value>
		#        </field>
		#      </x>
		#    </options>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		subscribe = SubElement(pubsub, 'subscribe', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})
		options_stanza = SubElement(pubsub, 'options')
		options_stanza.append(options)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_items_generic(self, server, node, specific=None, some=None, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""General method used to implement item requests.

		Retrieve items which have been published to node on server.

		If the optional argument specific is given as a list of item IDs
		then those items are retrieved.

		Replies are not yet handled."""

		If a number is supplied as the optional argument some then it is
		used as an upper limit the the number of items retrieved.
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		items = SubElement(pubsub, 'items', attrib={'node':str(node)})
		if some is not None:
			items.set('max_items', str(some))
		if specific is not None:
			for item in specific:
				items.append(Element('item', attrib={'id':item}))

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_all_items(self, server, node, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Retrieve all of the items published to node on server.

		Replies are not yet handled."""
		#<iq type='get' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <items node='my_blog'/>
		#  </pubsub>
		#</iq>
		self.request_items_generic(server, node, return_function=return_function, stanza_id)

	def request_specific_items(self, server, node, items, jid=None, return_function=None, stanza_id=None):		# FIXME NO HANDLER
		"""Retrieves certain items which have been published to node on
		server. items is a list of item IDs.

		Replies are not yet handled."""
		#<iq type='get' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <items node='my_blog'>
		#      <item id='an_id'/>
		#    </items>
		#  </pubsub>
		#</iq>
		self.request_items_generic(server, node, specific=items, return_function=return_function, stanza_id)

	def request_some_items(self, server, node, item_count, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Retrieves (at most) the last item_count items which have been
		published to node at server.

		Replies are not yet handled."""
		#<iq type='get' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <items node='my_blog' max_items='5'/>
		#  </pubsub>
		#</iq>
		self.request_items_generic(server, node, some=item_count, return_function=return_function, stanza_id)

	def publish(self, server, node, body, item_id=None, jid=None, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Publish body to the node node on server. If item_id is
		specified then request that it be used as the item's ID.

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <publish node='node'>
		#      <item id='item_id'>
		#.........body.............
		#        </entry>
		#      </item>
		#    </publish>
		#  </pubsub>
		#</iq>

		self.publish_with_options(server, node, body, item_id=item_id, jid=jid, return_function=return_function, stanza_id)

	def publish_with_options(self, server, node, body, options=None, item_id=None, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Generic method to implement all publishing requests.

		Publishes body as an item at node on server. If item_id is
		given then requests that it be used as the item's ID.

		options is not implemented sanely yet.

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <publish node='node'>
		#      <item id='item_id'>
		#			...body...
		#		</item>
		#    </publish>
		#    <publish-options>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#publish-options</value>
		#        </field>
		#        <field var='pubsub#access_model'>
		#          <value>presence</value>
		#        </field>
		#      </x>
		#    </publish-options>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		publish = SubElement(pubsub, 'publish', attrib={'node':str(node)})
		item = SubElement(publish, 'item')
		if item_id is not None:
			item.set('id', item_id)
		if type(body) == type(Element):
			item.append(body)
		elif type(body) == type("string"):
			item.text = body
		if options is not None:
			publish_options = SubElement(pubsub, 'publish-options')
			publish_options.append(options)

		def handler(stanza, callback):
			#<iq type='result'
			#    from='pubsub.shakespeare.lit'
			#    to='hamlet@denmark.lit/blogbot'
			#    id='publish1'>
			#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
			#    <publish node='princely_musings'>
			#      <item id='ae890ac52d0df67ed7cfdf51b644e901'/>
			#    </publish>
			#  </pubsub>
			print etree.tostring(stanza)
			if callback is not None:
				if stanza.get("type") == "result":
					callback(0)
				else:
					callback(stanza)

		print "Sending"
		self.send(stanza, handler, return_function)

	def delete_an_item_from_a_node(self, server, node, item_id, jid=None, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Removes the item with ID item_id from node at server.

		Replies are not handled yet."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <retract node='node'>
		#      <item id='item_id'/>
		#    </retract>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		retract = SubElement(pubsub, 'retract', attrib={'node':str(node)})
		item = SubElement(retract, 'item', attrib={'id':item_id})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_node(self, server, node, type, parent, options=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Asks the given server for a pubsub node. If node is None then
		an instant node is made, if it is a string or Node then that is
		used as the new node's ID. type can be 'collection' or 'leaf'
		the type type ('collection' or 'leaf').

		Not implemented completely sanely yet."""
		##FIXME: Explain the other options
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		create = SubElement(pubsub, 'create')

		# Instant nodes do not need a name
		if node is not None:
			create.set('node', str(node))

		configure = SubElement(pubsub, 'configure')

		# Nodes must have an option set to show that they are collections
		if type == 'collection':
			#      <x xmlns='jabber:x:data' type='submit'>
			#        <field var='FORM_TYPE' type='hidden'>
			#          <value>http://jabber.org/protocol/pubsub#node_config</value>
			#        </field>
			#        <field var='pubsub#node_type'><value>collection</value></field>
			#      </x>
			x = SubElement(configure, "x", attrib={"xmlns":"jabber:x:data", "type":"submit"})
			formtype_field = SubElement(x, "field", attrib={"var":"FORM_TYPE", "type":"hidden"})
			formtype_value = SubElement(formtype_field, "value")
			formtype_value.text = "http://jabber.org/protocol/pubsub#node_config"
			nodetype_field = SubElement(x, "field", attrib={"var":"pubsub#node_type"})
			nodetype_value = SubElement(nodetype_field, "value")
			nodetype_value.text = "collection"

		if options is not None:
			configure.append(options)

		def handler(stanza, callback):
			#<iq type='result'
			#	from='pubsub.shakespeare.lit'
			#	to='hamlet@denmark.lit/elsinore'
			#	id='create1'/>
			if callback is not None:
				if stanza.attrib.get("type") == "error":
					callback(False)
				elif stanza.attrib.get("type") == "result":
					callback(True)

		self.send(stanza, handler, return_function)

	def entity_request_instant_node(self, server, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Asks the given server for an instant node (ie. one without
		a predetermined name/id)."""
		#<iq type='set' from='us' to='them'>
		#    <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#      <create/>
		#      <configure/>
		#    </pubsub>
		#</iq>
		self.request_node(server, None, "leaf", None, None, return_function, stanza_id)

	def get_new_leaf_node(self, server, node, parent, options, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Requests a new leaf node (which can store items) with name
		node, as a sub-node of the node parent on server.

		options is not yet implemented sanely.

		Replies are not yet handled."""
		#<iq type='set' from='us' to='them'>
		#    <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#      <create node='my_blog'/>
		#      <configure/>
		#    </pubsub>
		#</iq>
		self.request_node(server, node, "leaf", parent, options, return_function, stanza_id)

	def get_new_collection_node(self, server, node, parent, options, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Requests a new collection node (which can store nodes) with
		name node, as a sub-node of the node parent on server.

		options is not yet implemented sanely.

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <create node='node_name'/>
		#    <configure>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#node_type'><value>collection</value></field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>
		self.request_node(server, node, "collection", parent, options, return_function, stanza_id)

	def get_new_leaf_node_nondefault_access(self, server, node, access_model, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set' from='us' to='them'>
		#    <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#      <create node='my_blog'/>
		#      <configure>
		#        <x xmlns='jabber:x:data' type='submit'>
		#          <field var='FORM_TYPE' type='hidden'>
		#            <value>http://jabber.org/protocol/pubsub#node_config</value>
		#          </field>
		#          <field var='pubsub#access_model'>
		#            <value>open</value>
		#          </field>
		#        </x>
		#      </configure>
		#    </pubsub>
		#</iq>"""

		x = Element('x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#node_config'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#access_model'})
		value2 = SubElement(field2, 'value')
		## FIXME: Add a check here
		value2.text = access_model

		self.entity_request_new_node_nondefault_configuration(server, node, x, stanza_id)

	def entity_request_new_node_nondefault_configuration(self, server, node, options, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <create node='my_blog'/>
		#    <configure>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#title'>
		#          <value>My Blog</value>
		#        </field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>

		self.request_node(server, node, options, return_function, stanza_id)

	def node_configuration_generic(self, server, node, options, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		stanza = Element('iq', attrib={'from':self.get_jid(), 'to':str(server)})
		if options is not None:
			stanza.set('type', 'set')
		else:
			stanza.set('type', 'get')
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		configure = SubElement(pubsub, 'configure', attrib={'node':str(node)})
		if options is not None:
			configure.append(options)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_node_configuration_form(self, server, node, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Request a form with which to configure node on server.

		Replies are not yet handled."""
		#<iq type='get' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='my_blog'/>
		#  </pubsub>
		#</iq>

		self.node_configuration_generic(server, node, None, stanza_id)

	def submit_node_configuration_form(self, server, node, options, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='my_blog'>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#title'>
		#          <value>Princely Musings (Atom)</value>
		#        </field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>

		self.node_configuration_generic(server, node, options, stanza_id)

	def cancel_node_configuration(self, server, node, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Retracts a request to reconfigure node on server.

		Replies are not yet handled."""
		#<iq type='set' from='us' to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='my_blog'>
		#      <x xmlns='jabber:x:data' type='cancel'/>
		#    </configure>
		#  </pubsub>
		#</iq>
		x = Element(configure, 'x', attrib={'xmlns':'jabber:x:data', 'type':'cancel'})

		self.submit_node_configuration_form(server, node, x, stanza_id)

	def request_default_configuration_options(self, server, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Asks server for the configuration which is used as default
		for new nodes.

		Replies are not yet handled."""
		#<iq type='get'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <default/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		default = SubElement(pubsub, 'default')

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_default_collection_configuration(self, server, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Ask server for the options which are applied by default to
		new collection nodes.

		Replies are not yet handled."""
		#<iq type='get'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <default>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#node_type'><value>collection</value></field>
		#      </x>
		#    </default>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		default = SubElement(pubsub, 'default')
		x = SubElement(default, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#node_config'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#node_type'})
		value2 = SubElement(field2, 'value')
		value2.text = 'collection'

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def delete_a_node(self, server, node, return_function=None, stanza_id=None):
		"""Delete the given node from the given server.

		If given, return_function is run upon reply with a value of
		True if the deletion was successful, or False if there was an
		error."""
		## FIXME: Give different results for different types of error.
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <delete node='node_name'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		delete = SubElement(pubsub, 'delete', attrib={'node':str(node)})

		def handler(stanza, callback):
			#<iq type='result'
			#    from='pubsub.shakespeare.lit'
			#    id='delete1'/>
			if callback is not None:
				if stanza.get("type") == "result":
					callback(True)
				elif stanza.get("type") == "error":
					callback(False)


		self.send(stanza, handler, return_function)

	def purge_all_items_from_a_node(self, server, node, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Remove every item which has been published to node on server.

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <purge node='node_name'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		purge = SubElement(pubsub, 'purge', attrib={'node':str(node)})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_pending_subscription_requests(self, server, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Get every relevant request for subscription for nodes at
		server.

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <command xmlns='http://jabber.org/protocol/commands'
		#           node='http://jabber.org/protocol/pubsub#get-pending'
		#           action='execute'/>
		#</iq>"""
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		command = SubElement(stanza, 'command', attrib={'xmlns':'http://jabber.org/protocol/commands', 'node':'http://jabber.org/protocol/pubsub#get-pending', 'action':'execute'})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_pending_subscription_requests_for_a_node(self, server, node, time, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Ask server for every subscription request which has not yet
		been handled for node.

		Not yet implemented sanely."""
		## FIXME: Check spec, no "from"??!
		#<iq type='set' to='them'>
		#  <command xmlns='http://jabber.org/protocol/commands'
		#           sessionid='pubsub-get-pending:20031021T150901Z-600'
		#           node='http://jabber.org/protocol/pubsub#get-pending'
		#           action='execute'>
		#    <x xmlns='jabber:x:data' type='submit'>
		#      <field var='pubsub#node'>
		#        <value>node_name</value>
		#      </field>
		#    </x>
		#  </command>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		command = SubElement(stanza, 'command', attrib={'xmlns':'http://jabber.org/protocol/commands', 'sessionid':'pubsub-get-pending:' + time, 'node':'http://jabber.org/protocol/pubsub#get-pending', 'action':'execute'})
		x = SubElement(command, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'pubsub#node'})
		value1 = SubElement(field1, 'value')
		value1.text = str(node)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_all_subscriptions(self, server, node, return_function=None, stanza_id=None):
		"""Redundant"""
		#<iq type='get'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <subscriptions node='node_name'/>
		#  </pubsub>
		#</iq>
		self.retrieve_subscriptions(server, node, return_function, stanza_id)

	def modify_subscriptions(self, server, node, subscriptions, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented in a sane way."""
		#<iq type='set'
		#    from='them'
		#    to='us'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <subscriptions node='node_name'>
		#      <subscription jid='current_jid' subscription='subscribed'/>
		#    </subscriptions>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		subscriptions = SubElement(pubsub, 'subscriptions', attrib={'node':str(node)})
		for current_jid in subscriptions.keys():
			subscriptions.append(Element('subscription', attrib={'jid':current_jid, 'subscription':subscriptions[current_jid]}))

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def multiple_simultaneous_modifications(self, server, node, subscriptions, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented in a sane way."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <subscriptions node='node_name'>
		#      <subscription jid='current_subscription' subscription='subscribed'/>
		#    </subscriptions>
		#  </pubsub>
		#</iq>
		stanza = ElementTree('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		subscriptions = SubElement(pubsub, 'subscriptions', attrib={'node':str(node)})
		for current_subscription in subscriptions.keys():
			subscriptions.append(Element('subscription', attrib={'jid':current_subscription, 'subscription':subscriptions[current_subscription]}))

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def request_all_affiliated_entities(self, server, node, return_function=None, stanza_id=None):
		"""Asks server for all entities (JIDs) affiliated in some way to
		node.

		An affiliation is owner, publisher or outcast. It does not
		include subscribers.

		If return_function is given, it is called upon reply with one
		argument of False if there was an error, or if it was successful
		a dictionary of the form:

		{'publisher':[JID1, JID2, ...], 'owner':[JID3, JID4, ...], ...}"""
		#<iq type='get'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <affiliations node='node'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		affiliations = SubElement(pubsub, 'affiliations', attrib={'node':str(node)})

		def handler(stanza, callback):
			#<iq xmlns="jabber:client"
			#    to="test1@localhost/subscriptions"
			#    from="pubsub.localhost"
			#    type="result">
			#    <pubsub xmlns="http://jabber.org/protocol/pubsub#owner">
			#        <affiliations node="/home/localhost/test1">
			#            <affiliation affiliation="owner" jid="test1@localhost"/>
			#        </affiliations>
			#    </pubsub>
			#</iq>
			if callback is not None:
				if stanza.get('type') == 'error':
					affiliation_dictionary = False
				elif stanza.get('type') == 'result':
					affiliations = stanza.find('.//{http://jabber.org/protocol/pubsub#owner}affiliations')
					affiliation_dictionary = {}
					if affiliations is not None:
						for affiliation in affiliations:
							if not affiliation.get("affiliation") in affiliation_dictionary.keys():
								affiliation_dictionary[affiliation.get("affiliation")] = []
							affiliation_dictionary[affiliation.get("affiliation")].append(JID(affiliation.get("jid")))
				callback(affiliation_dictionary)

		self.send(stanza, handler, return_function)

	def modify_affiliation(self, server, node, affiliations, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Tells server to change the affiliation of some entities to
		the node node. affiliations is a dictionary of the form:

		{JID1:affiliation_type, JID2:affiliation_type, ...}

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <affiliations node='node'/>
		#      <affiliation jid='current_affiliation' affiliation='affiliations'/>
		#    </affiliations>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		affiliations_element = SubElement(pubsub, 'affiliations', attrib={'node':str(node)})
		for current_affiliation in affiliations.keys():
			affiliations_element.append(Element('affiliation', attrib={'jid':str(current_affiliation), 'affiliation':affiliations[current_affiliation]}))

		def handler(stanza, callback):
			print etree.tostring(stanza)
			if callback is not None:
				if stanza.get("type") == "result":
					callback(0)
				else:
					callback("error")

		self.send(stanza, handler, return_function)

	def subscribe_to_a_collection_node(self, server, node, jid, return_function=None, stanza_id=None):		#FIXME REDUNDANT?
		"""Not yet implemented in a sane way"""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscribe jid='jid'
		#               node='node_name'/>
		#   </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		subscribe = SubElement(pubsub, 'subscribe', attrib={'jid':self.get_jid(jid, True), 'node':str(node)})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def subscribe_to_collection_node_with_configuration(self, server, node, options, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented in a sane way."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscribe jid='jid'
		#               node='node_name'/>
		#    <options>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#subscribe_options</value>
		#        </field>
		#        <field var='pubsub#subscription_type'>
		#          <value>items</value>
		#        </field>
		#        <field var='pubsub#subscription_depth'>
		#          <value>all</value>
		#        </field>
		#      </x>
		#   </options>
		# </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		subscribe = SubElement(pubsub, 'subscribe', attrib={'jid':self.get_jid(jid, True), 'node':str(node)})
		options_element = SubElement(pubsub, 'options')
		options_element.append(options)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def subscribe_to_root_collection_node(self, server, jid=None, return_function=None, stanza_id=None):		#FIXME NO HANDLER XEP-0248?
		"""Subscribe jid (or, if not supplied, the currently logged-in
		JID) to the root collection node (the node which contains all
		of the nodes) on server.

		Replies are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscribe jid='jid'/>
		# </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		subscribe = SubElement(pubsub, 'subscribe', attrib={'jid':self.get_jid(jid, True)})

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def create_a_new_node_associated_with_a_collection(self, server, node, collection, return_function=None, stanza_id=None):		#FIXME NO HANDLER
		"""Request a new node with name node on server server. The new
		node will be a sub-node of the node collection.

		Results are not yet handled."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <create node='node_name'/>
		#    <configure>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='pubsub#collection'><value>collection_name</value></field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		create = SubElement(pubsub, 'create', attrib={'node':str(node)})
		configure = SubElement(pubsub, 'configure')
		x = SubElement(configure, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'pubsub#collection'})
		value1 = SubElement(field1, 'value')
		value1.text = str(collection)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def modify_node_configuration(self, server, node, collection, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		# Sets node_name as member of collection_name
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='node'>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#collection'><value>collection</value></field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		configure = SubElement(pubsub, 'configure', attrib={'node':str(node)})
		x = SubElement(configure, 'x', attrib={'xmlns':'jaber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#node_config'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#collection'})
		value2 = SubElement(field2, 'value')
		value2.text = str(collection)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def modify_collection_configuration(self, server, node, collection, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		# Make node_name a child of collection_name
		## FIXME: This MUST include the current children too, but doesn't at the mo'
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='collection'>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#children'>
		#          <value>node</value>
		#        </field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		configure = SubElement(pubsub, 'configure', attrib={'node':str(collection)})
		x = SubElement(configure, 'x', attrib={'xmlns':'jaber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#node_config'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#children'})
		value2 = SubElement(field2, 'value')
		value2.text = str(node)

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def disassociate_collection_from_a_node(self, server, node, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely"""
		## FIXME: This disassociates from EVERY collection. Should be able to specify collections
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='node'>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#collection'><value></value></field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		configure = SubElement(pubsub, 'configure', attrib={'node':str(node)})
		x = SubElement(configure, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#node_config'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#collection'})
		value2 = SubElement(field2, 'value')
		value2.text = ''

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def disassociate_node_from_a_collection(self, server, node, collection, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not implemented sanely yet"""
		## FIXME: Needs fixing badly. This clears all children from the node
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
		#    <configure node='collection'>
		#      <x xmlns='jabber:x:data' type='submit'>
		#        <field var='FORM_TYPE' type='hidden'>
		#          <value>http://jabber.org/protocol/pubsub#node_config</value>
		#        </field>
		#        <field var='pubsub#children'>
		#          <value>add children here, minus node</value>
		#        </field>
		#      </x>
		#    </configure>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#owner'})
		configure = SubElement(pubsub, 'configure', attrib={'node':str(collection)})
		x = SubElement(configure, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#node_config'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#children'})
		value2 = SubElement(field2, 'value')
		value2.text = ''		# sould be all current children, except for node

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def time_based_subscribe(self, server, node, expire_time, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <options node='node_name' jid='jid'>
		#        <x xmlns='jabber:x:data' type='submit'>
		#          <field var='FORM_TYPE' type='hidden'>
		#            <value>http://jabber.org/protocol/pubsub#subscribe_options</value>
		#          </field>
		#          <field var='pubsub#expire'><value>expire_time</value></field>
		#        </x>
		#     </options>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub#subscription_options'})
		options = SubElement(pubsub, 'options', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})
		x = SubElement(options, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#subscribe_options'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#expire'})
		value2 = SubElement(field2, 'value')
		value2.text = expire_time

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def renew_lease(self, server, node, new_expire, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set'
		#    from='us'
		#    to='them'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <options node='node_name' jid='jid'>
		#        <x xmlns='jabber:x:data' type='submit'>
		#          <field var='FORM_TYPE' type='hidden'>
		#            <value>http://jabber.org/protocol/pubsub#subscribe_options</value>
		#          </field>
		#          <field var='pubsub#expire'><value>new_expire</value></field>
		#        </x>
		#     </options>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		options = SubElement(pubsub, 'options', attrib={'node':str(node), 'jid':self.get_jid(jid, True)})
		x = SubElement(options, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#subscribe_options'
		field2 = SubElement(x, 'field', attrib={'var':'pubsub#expire'})
		value2 = SubElement(field2, 'value')
		value2.text = new_expire

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def keyword_filtered_subscription(self, server, node, subid, filters, jid=None, return_function=None, stanza_id=None):		#FIXME A LOT
		"""Not yet implemented sanely."""
		#<iq type='set'
		#    from='bard@shakespeare.lit/globe'
		#    to='pubsub.shakespeare.lit'
		#    id='filter3'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <options node='node'
		#             jid='ourjid'
		#             subid='subid'>
		#        <x xmlns='jabber:x:data' type='submit'>
		#          <field var='FORM_TYPE' type='hidden'>
		#            <value>http://jabber.org/protocol/pubsub#subscribe_options</value>
		#          </field>
		#          <field var='http://shakespeare.lit/search#keyword'><value>filters</value></field>
		#        </x>
		#     </options>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'set', 'from':self.get_jid(), 'to':str(server)})
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		options = SubElement(pubsub, 'options', attrib={'node':str(node), 'jid':self.get_jid(jid, True), 'subid':subid})
		x = SubElement(options, 'x', attrib={'xmlns':'jabber:x:data', 'type':'submit'})
		field1 = SubElement(x, 'field', attrib={'var':'FORM_TYPE', 'type':'hidden'})
		value1 = SubElement(field1, 'value')
		value1.text = 'http://jabber.org/protocol/pubsub#subscribe_options'
		filter_field = SubElement(x, 'field', attrib={'var':'http://shakespeare.lit/search#keyword'})
		filter_value = SubElement(filter_field, "value")
		filter_value.text = filters		## FIXME: Desperately :P

		def handler(stanza, callback):
			print etree.tostring(stanza)

		self.send(stanza, handler, return_function)

	def retrieve_subscriptions(self, server, node=None, return_function=None, stanza_id=None):
		"""Retrieve any subscriptions which the current account has on
		the given server. If a node is given, retrieve any subscriptions
		which the current account has on the given node on the given
		server.

		If given, return_function is run upon a reply being received with
		a dictionary in the format
		{server_name:{node_name:{'jid':subscribed_jid, 'state':subscription_state, 'subid':subscription_id}}}
		where 'jid', 'state' and 'subid' are literally those strings,
		whilst server_name is the address of the server, node_name is a
		string of the node ID, subscribed_jid is a string of the JID
		used to subscribe to this node (which may include a resource,
		depending on how the subscription was made), subscription_state
		is a string of 'subscribed', 'pending' or 'unconfigured' and
		subscription_id is an optional string of this subscription's
		unique ID (depending whether the server gives subscriptions an
		ID or not).

		If an error is received, the return_function is run with False."""
		# Server
		#<iq type='get'
		#    from='francisco@denmark.lit/barracks'
		#    to='pubsub.shakespeare.lit'
		#    id='subscriptions1'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscriptions/>
		#  </pubsub>
		#</iq>
		#Node
		#<iq type='get'
		#    from='francisco@denmark.lit/barracks'
		#    to='pubsub.shakespeare.lit'
		#    id='subscriptions2'>
		#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
		#    <subscriptions node='princely_musings'/>
		#  </pubsub>
		#</iq>
		stanza = Element('iq', attrib={'type':'get', 'from':self.get_jid(), 'to':str(server)})		# Is it correct to use self.server here?
		pubsub = SubElement(stanza, 'pubsub', attrib={'xmlns':'http://jabber.org/protocol/pubsub'})
		if node is not None:
			subscriptions = SubElement(pubsub, 'subscriptions', attrib={'node':str(node)})
		else:
			subscriptions = SubElement(pubsub, 'subscriptions')
		def handler(stanza, callback):
			#Subscriptions
			#<iq type='result'
			#    from='pubsub.shakespeare.lit'
			#    to='francisco@denmark.lit'
			#    id='subscriptions1'>
			#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
			#    <subscriptions>
			#      <subscription node='node1' jid='francisco@denmark.lit' subscription='subscribed'/>
			#      <subscription node='node2' jid='francisco@denmark.lit' subscription='subscribed'/>
			#      <subscription node='node5' jid='francisco@denmark.lit' subscription='unconfigured'/>
			#      <subscription node='node6' jid='francisco@denmark.lit' subscription='pending'/>
			#    </subscriptions>
			#  </pubsub>
			#</iq>
			#No Subscriptions
			#<iq type='result'
			#    from='pubsub.shakespeare.lit'
			#    to='francisco@denmark.lit/barracks'
			#    id='subscriptions1'>
			#  <pubsub xmlns='http://jabber.org/protocol/pubsub'>
			#    <subscriptions/>
			#  </pubsub>
			#</iq>

			# Don't bother doing anything if we aren't going to act anyway
			if callback is not None:
				# Report errors as False
				if stanza.get('type') == 'error':
					callback(False)
				# If we get a successful reply, there's a bit more work to do
				elif stanza.get('type') == 'result':
					# Get server name
					reply_server = stanza.get('from')
					# Initialise an empty dictionary
					subscriptions_dict = {reply_server:{}}
					# Look for any <subscriptions> elements
					for subscriptions in stanza.xpath(".//{http://jabber.org/protocol/pubsub}subscriptions"):
						# Look inside the <subscriptions> element for actual subscriptions
						for subscription in subscriptions.xpath(".//{http://jabber.org/protocol/pubsub}subscription"):
							# The subid attribute is optional, so check for it
							if subscription.get('subid') is not None:
								# If found then construct the reply using it
								subscriptions_dict[reply_server][subscription.get('node')] = {\
									'jid':subscription.get('jid'), \
									'state':subscription.get('subscription'), \
									'subid':subscription.get('subid')}
							else:
								# If not found then construct the reply without it
								subscriptions_dict[reply_server][subscription.get('node')] = {\
									'jid':subscription.get('jid'), \
									'state':subscription.get('subscription')}
					# Run the callback with the derived reply
					callback(subscriptions_dict)

		self.send(stanza, handler, return_function)

class Node(object):
	"""Pointer to a PubSub Node."""

	def __init__(self, server=None, name=None, jid=None, type=None, parent=None):
		self.set_server(server)
		self.set_name(name)
		self.set_jid(jid)
		self.set_type(type)
		self.set_parent(parent)

	def __str__(self):
		return self.name

	def set_server(self, server):
		"""Sets the server which this Node object points to (does NOT
		edit any actual nodes, only this pointer!)"""
		if type(server) == type("string"):
			self.server = Server(server)
		elif type(server) == type(Server()):
			self.server = server
		else:
			print "Error: server must be a string or a Server."

	def set_name(self, name):
		"""Sets the node name which this Node object points to (does NOT
		edit any actual nodes, only this pointer!)"""
		self.name = str(name)

	def set_jid(self, jid):
		self.jid = jid

	def set_type(self, type):
		"""Sets the type of this Node object. Does not edit the actual
		node."""
		self.type = type

	def set_parent(self, parent):
		"""Sets the parent collection node of this Node object. Does
		not edit the actual node."""
		self.parent = parent

	def get_sub_nodes(self, client, callback=None):
		"""Queries this node for its children. Passes a list of Nodes
		it finds to the return_function when a reply is received."""
		client.get_nodes(self.server, self, return_function=callback)

	def get_items(self, client, callback=None):
		"""TODO: Queries this node for the items it contains. Returns a list
		of the strings contained in the items."""
		client.get_items(self.server, self.name, return_function=callback)

	def get_information(self, client, callback=None):
		client.get_node_information(self.server, self, return_function=callback)

	def make_sub_node(self, client, name, type, callback=None):
		if self.type is "leaf":
			raise TypeError('Leaf nodes cannot contain child nodes')
		else:
			if self.type is None:
				print "Warning: Node type is not known, yet child node requested. This will fail for leaf nodes."
			if type == 'leaf':
				client.get_new_leaf_node()
			elif type == 'collection':
				client.get_new_collection_node()

	def request_all_affiliated_entities(self, client, return_function=None):
		client.request_all_affiliated_entities(self.server, self, return_function)

	def modify_affiliations(self, client, affiliation_dictionary, return_function=None):
		client.modify_affiliation(self.server, self, affiliation_dictionary, return_function)

	def publish(self, client, body, id=None, return_function=None):
		client.publish(self.server, self, body, id, None, return_function)

	def subscribe(self, client, jid, return_function=None):
		client.subscribe(self.server, self, jid, return_function)

class Server(object):

	def __init__(self, name=None):
		if name is not None:
			self.set_name(name)

	def set_name(self, name):
		self.name = name

	def __str__(self):
		return self.name

	def add_node(self, client, name, callback=None):
		client.request_node(self, name, None, None, return_function=callback)

class JID(xmpp.JID, object):

	def __init__(self, string='none@none'):
		super(JID, self).__init__(string)
		self.name = str(self)

class Item(object):
	"""Something which has been, or can be, published to a Node."""

	def __init__(name=None, jid=None, node=None):
		self.name = name
		self.jid = jid
		self.node = node
