import os
import sys
import optparse
import bottle
import socket
#import logging
import json
import helper

# patch socket module;
# by default bottle doesn't set address as reusable
# and there is no option to do it...
socket.socket._bind = socket.socket.bind

def my_socket_bind(self, *args, **kwargs):
    self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return socket.socket._bind(self, *args, **kwargs)
socket.socket.bind = my_socket_bind

@bottle.route('/')
def main():
    return serve_static_file("app.html")

@bottle.route("/<url:path>")
def serve_static_file(url):
    return bottle.static_file(url, os.path.dirname(__file__))

@bottle.post("/calculate")
def do_calculation():
    user_input = json.load(bottle.request.body)

    print("received:", user_input)
    # we have received attenuators, peaks, beam_energy,
    # multilayer, materials, detector, incoming_angle, outgoing_angle
    text = "The answer is 42."
    try:
        text = helper.getMultilayerFluorescence(user_input)
    except:
        text = ("ERROR: %s" % sys.exc_info()[1])
    return { "text": text }

def serve_forever(port=None):
    bottle.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    usage = "usage: \%prog [-p<port>]" 

    parser = optparse.OptionParser(usage)
    parser.add_option(
        '-p', '--port', dest='port', type='int',
        help='Port to listen on (default 8099)', default=8099, action='store')
    options, args = parser.parse_args()

    #logging.basicConfig()
    #logging.getLogger().setLevel(logging.DEBUG)

    serve_forever(options.port)
