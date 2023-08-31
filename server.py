"""COSC264 Socket Programming Assignment
Author: Sam Willems 31643284
"""

import sys
from socket import *


class Message:
    """Defines a message class to store client messages as."""
    
    def __init__(self, msg_data, name_len, recv_len, msg_len):
        # Defines the indexes for where each piece of data starts
        recv_idx = name_len
        msg_idx = recv_idx + recv_len

        # Decodes the different fields
        self.name = msg_data[:recv_idx].decode("utf-8")
        self.recv_name = msg_data[recv_idx:msg_idx].decode("utf-8")
        self.msg = msg_data[msg_idx:].decode("utf-8")


    def __str__(self):
        return f"{self.name} {self.recv_name} {self.msg}"


def get_valid_port():
    """Returns a port number if the sys port argument is within the allowed range.
    prints an error message if it is not in the allowed range."""
    port = sys.argv[1]
    if not 1024 <= int(port) <= 64000:
        print("ERROR: Port number must be in range 1024 - 60000 (inclusive)")
        sys.exit()
    return int(port)


def process_msg(conn):
    """Checks that a message request is valid. If not, raises a ValueError.
    Returns a Message object containing the clients message."""
    msg = bytearray(conn.recv(7))

    # Check length (header)
    if len(msg) < 7:
        raise ValueError("Received message is erroneous [too short]")

    # Check magic number
    if (msg[0] << 8) + msg[1] != 0xAE73:
        raise ValueError("Received message is erroneous [incorrect MagicNo]")
    
    # Check ID
    if msg[2] not in [1, 2]:
        raise ValueError("Received message is erroneous [incorrect ID]")
    else:
        msg_type = "read" if (msg[2] == 1) else "create"
    
    # Check NameLen
    if msg[3] < 1:
        raise ValueError("Received message is erroneous [NameLen less than 1]")

    # Check ReceiverLen
    if (msg_type == "read" and msg[4] != 0) or (msg_type == "create" and msg[4] < 1):
        raise ValueError("Received message is erroneous [erroneous RecieverLen]")

    # Check MessageLen
    msg_len = (msg[5] << 8) + msg[6]
    if (msg_type == "read" and msg_len != 0) or (msg_type == "create" and msg_len < 1):
        raise ValueError("Received message is erroneous [erroneous MessageLen]")
    
    # Check total length
    total_len = msg[3] + msg[4] + msg_len
    msg.extend(conn.recv(total_len + 1))
    if len(msg) != total_len + 7:
        raise ValueError("Received message is erroneous [incorrect length]")
    
    # Gets the username
    username_len = msg[3]
    username = msg[7:7 + username_len].decode("utf-8")

    # Creates the Message object if it is a create message.
    if msg_type == "create":
        message = Message(msg[7:], msg[3], msg[4], msg_len)
        
        # Gets the receiver name
        recv_name_len = msg[4]
        recv_name = msg[7 + username_len: 7 + username_len + recv_name_len].decode("utf-8")

        print(f"SERVER: Message sent from {username} to {recv_name}")
        return message, username
    return None, username


def build_message_response(msg_list, username):
    """Builds a MessageResponse containing the messages that have been left for the user of the given
    username."""
    response = bytearray(5) # fixed header
    available_msgs = [msg for msg in msg_list if msg.recv_name == username]
    
    # Magic number
    response[0] = 0xAE
    response[1] = 0x73

    # ID
    response[2] = 3

    # Num items
    num_items = len(available_msgs)
    response[3] = num_items if num_items <= 255 else 255

    # More messages
    response[4] = 0 if num_items <= 255 else 1

    # Messages to send to the client
    counter = 0
    while len(available_msgs) > 0 and counter <= 255:
        msg = available_msgs[0]

        # Message header
        msg_bytes = bytearray(3)

        # SenderLen
        msg_bytes[0] = len(msg.name)
        
        # MessageLen
        msg_bytes[1] = (len(msg.msg) & 0xFF00) >> 8
        msg_bytes[2] = len(msg.msg) & 0xFF

        # text
        msg_bytes.extend(msg.name.encode("utf-8"))
        msg_bytes.extend(msg.msg.encode("utf-8"))

        # Add to response
        response.extend(msg_bytes)

        # Removes message from list of messages
        msg_list.pop(0)
        available_msgs.pop(0)
        counter += 1
    
    return response, counter


def main():
    """Runs the server application."""
    sock = None
    conn = None

    try:
        # Checks program arguments.
        filename = sys.argv[0]

        if len(sys.argv) != 2:
            print(f"Usage:\npython(3) {filename} <port>\n")
            sys.exit()

        port = get_valid_port()
        client_msgs = []

        # Creates the socket.
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(("0.0.0.0", port))

        # Starts listening for requests on the socket.
        sock.listen(5)

        while True: # Starts the main loop. 
            try:
                # Accepts a connection from the client.
                conn, client = sock.accept()
                conn.settimeout(1)
                print(f"CONNECTION: {client[0]} on port {port}")

                # Gets a message from the client and checks it.
                msg_obj, username = process_msg(conn)

                # Adds message to list of messages if it is a create message.
                if msg_obj != None:
                    client_msgs.append(msg_obj)
                
                # If the client sends a read request, sends MessageResponse back
                if msg_obj == None:
                    response, num_msgs = build_message_response(client_msgs, username)
                    conn.sendall(response)
                    print(f"SERVER: {num_msgs} messages sent to {client[0]}")

            # Error handling
            except timeout:
                print(f"ERROR: Message timeout")
            
            except OSError as err:
                print(f"ERROR: {err}")
            
            except ValueError as err:
                print(f"ERROR: {err}")

            finally:
                if conn != None:
                    conn.close()


    except ValueError: # Port int conversion
        print(f"ERROR: Port {sys.argv[1]} is not an integer")
    
    finally:
        if sock != None:
            sock.close()


main()

