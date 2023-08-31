"""COSC264 Socket Programming Assignment
Author: Sam Willems 31643284
"""

import sys
import time
from socket import *


def get_valid_port():
    """Returns a port number if the sys port argument is within the allowed range.
    Raises a ValueError if it is not in the allowed range."""
    port = sys.argv[2]
    if not 1024 <= int(port) <= 64000:
        raise ValueError("Port number must be in range 1024 - 60000 (inclusive)")
    
    return int(port)


def get_valid_address(port):
    """Returns an address if the given hostname or IP address is valid otherwise raises a ValueError."""
    address = None
    try:
        address = getaddrinfo(sys.argv[1], port, AF_INET, SOCK_STREAM)[0][-1]
    except gaierror:
        raise ValueError(f"{sys.argv[1]} is not a valid hostname or IP address")
        sys.exit()
    

    return address


def get_valid_username():
    """Returns the given username in sys.args if it is at least one character and its length in bytes is
    <= 255. Otherwise raises a ValueError."""
    name = sys.argv[3]
    name_bytes = name.encode('utf-8')
    if len(name) < 1:
        raise ValueError(f"Username must be at least 1 character")
        sys.exit()
    if len(name_bytes) > 255:
        raise ValueError(f"Username is too long")
        sys.exit()
    return name


def get_valid_request_type():
    """Returns the request type if it is either 'read' or 'create' otherwise raises a ValueError."""
    req = sys.argv[4]
    if req != "read" and req != "create":
        raise ValueError("Request type must be read or create")
    return req


def get_reciever_name():
    """Returns the reciever name when a valid name is given. Keeps asking until appropriate name is given."""
    valid = False
    while not valid:
        name = input("Reciever name: ")
        if len(name) < 1:
            print("ERROR: Reciever name must be at least one character")
        elif len(name.encode("utf-8")) >= 255:
            print("ERROR: Reciever name is too long")
        else:
            valid = True
    return name


def get_message_contents():
    """Returns the message given by the user when they input a valid message. Otherwise will ask again for
    a valid message."""
    valid = False
    while not valid:
        msg = input("message: ")
        if len(msg) < 1:
            print("ERROR: Message must be at least one character")
        elif len(msg.encode("utf-8")) >= 65535:
            print("ERROR: Message name is too long")
        else:
            valid = True
    return msg


def build_message_request(req_type, username):
    """Builds a message request to be sent to the server from the client."""
    msg = bytearray(7) # Defines 7 bytes for the fixed header.

    # Magic number
    msg[0] = 0xAE
    msg[1] = 0x73
    
    # ID
    msg[2] = 1 if req_type == "read" else 2

    # Username length
    msg[3] = len(username.encode("utf-8"))

    # Username
    msg.extend(username.encode('utf-8'))

    # Reciever name and length
    if req_type == "create":
        reciever_name = get_reciever_name()
        msg[4] = len(reciever_name.encode("utf-8"))
        msg.extend(reciever_name.encode("utf-8"))
    
        # Message content length
        msg_content = get_message_contents()
        msg[5] |= (len(msg_content.encode("utf-8")) & 0xFF00) >> 8
        msg[6] |= len(msg_content.encode("utf-8")) & 0xFF
        msg.extend(msg_content.encode("utf-8"))

    return msg


def process_message_response(sock):
    """Processes a message response."""
    response = bytearray(sock.recv(5))
    # Check initial length
    if len(response) < 5:
        raise ValueError("Received message is erroneous [too short]")
    
    # Check magic number
    if (response[0] << 8) + response[1] != 0xAE73:
        raise ValueError("Received message is erroneous [incorrect MagicNo]")
    
    # Check ID
    if response[2] != 3:
        raise ValueError("Received message is erroneous [incorrect ID]")
    
    # Check MoreMsgs
    if response[4] not in [0, 1]:
        raise ValueError("Received message is erroneous [incorrect MoreMsgs]")
    
    # Process messages
    num_items = response[3]
    counter = 1

    # Lets the client know if there are no messages
    if num_items == 0:
        print("SERVER: There are no messages to be read")   
        return 

    while num_items > 0:
        header = sock.recv(3)

        # Check SenderLen
        sender_len = header[0]
        if sender_len < 1:
            raise ValueError(f"Received message is erroneous [SenderLen too short on msg #{counter}]")
        
        # Check MessageLen
        message_len = (header[1] << 8) + header[2]
        if message_len < 1:
            raise ValueError(f"Received message is erroneous [MessageLen too short on msg #{counter}]")
        
        # Print message
        data = sock.recv(sender_len + message_len)
        sender = data[:sender_len].decode("utf-8")
        msg = data[sender_len:].decode("utf-8")
        print(f"{sender}: {msg}")

        counter += 1
        num_items -= 1
    
    # Lets the client know if there were more than 255 messages to read
    if response[4] == 1:
        print("SERVER: More messages are available to be read")


def main():
    """Runs the client application."""
    sock = None

    try:
        # Gets relevant informantion from sys.argv or exits if information is invalid
        if len(sys.argv) != 5:
            print(f"Usage:\npython(3) {sys.argv[0]} <hostname|IP_address> <port> <username> <read|create>\n")
            sys.exit()
        port = get_valid_port()
        address = get_valid_address(port)
        username = get_valid_username()
        request_type = get_valid_request_type()

        # Build message request
        msg_req = build_message_request(request_type, username)

        # Connects to the server
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect(address)
        sock.settimeout(1)

        # Sends the MessageRequest to the server.
        amount = sock.send(msg_req)
        if amount < len(msg_req):
            raise OSError("Unable to send whole message")
        
        # Processes the messages that have been sent from the server to the user if a read is requested.
        if request_type == "read":
            process_message_response(sock)


    # Error handling
    except ValueError as err:
        print(f"ERROR: {err}")

    except timeout:
        print("ERROR: Message timeout")

    except OSError as err:
        print(f"ERROR: {err}")
    
    finally:
        if sock != None:
            sock.close()


main()

