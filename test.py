#!/usr/bin/env python
import pubsubclient
import time

# This will run when we get a reply
def handle_nodes(node_list):
	# This function should take one argument, a list of pubsubclient.Node objects
	global client
	# We've received a reply, so reduce the amount we're waiting for by one
	global wait
	wait -= 1

	for node in node_list:
		print "Found node " + str(node)		# str on a Node will give its name/ID
		# Now we can request this Node's children
		# We need to supply a PubSubClient to use and a return function
		node.get_sub_nodes(client, handle_nodes)
		# We're now waiting for another reply, so increment wait
		wait += 1


global wait
global client
# Make a client
client = pubsubclient.PubSubClient("test1@localhost", "test")
# Log on
client.connect()

# The following line requests the top-level nodes on aserver.com and makes handle_nodes the return function
client.get_nodes('pubsub.localhost', node=None, return_function=handle_nodes)

# This keeps track of how many replies we are waiting on
# Needs to be global since we're using it in the function too
wait = 1
while wait > 0:
	# Handle any replies
	client.process()
	# Wait for a second
	time.sleep(1)
# Now we can close
