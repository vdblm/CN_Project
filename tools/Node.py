import warnings

from tools.simpletcp.clientsocket import ClientSocket
import logging

logging.basicConfig(format='%(asctime)s %(message)s')


class Node:
    def __init__(self, server_address, set_register=False):
        """
        The Node object constructor.

        This object is our low-level abstraction for other peers in the network.
        Every node has a ClientSocket that should bind to the Node TCPServer address.

        Warnings:
            1. Insert an exception handler when initializing the ClientSocket; when a socket closed here we will face to
               an exception and we should detach this Node and clear its output buffer.

        :param server_address:
        :param set_register:
        """
        self.server_ip = Node.parse_ip(server_address[0])
        self.server_port = Node.parse_port(server_address[1])

        self.server_address = (self.server_ip, self.server_port)

        logging.warning("Node added with Server Address: " + str(self.server_address))

        self.out_buff = []
        self.is_register = set_register

        # TODO im not sure of this.
        try:
            self.client = ClientSocket(mode=self.server_ip, port=int(self.server_port))
        except:
            logging.warning('Exception in creating the client socket for node: ' + str(self.server_address))
            # Detaching the node???
            self.out_buff.clear()
            raise Exception

    def send_message(self):
        """
        Final function to send buffer to the client's socket.

        :return:
        """
        # TODO I'm not sure of this. Do we need to check the response of client sending (to be b'ACK')
        for msg in self.out_buff:
            res = self.client.send(bytes(msg))
            logging.info('sent message: ' + str(bytes(msg)) + ' to ' + str(self.server_address))
            if res != b'ACK':
                logging.warning('not received b\'ACK\' for node: ' + str(self.server_address))

        self.out_buff.clear()

    def add_message_to_out_buff(self, message):
        """
        Here we will add a new message to the server out_buff, then in 'send_message' will send them.

        :param message: The message we want to add to out_buff
        :return:
        """
        self.out_buff.append(message)

    def close(self):
        """
        Closing client's object.
        :return:
        """
        self.client.close()

    def get_server_address(self):
        """

        :return: Server address in a pretty format.
        :rtype: tuple
        """
        return self.server_address

    @staticmethod
    def parse_ip(ip):
        """
        Automatically change the input IP format like '192.168.001.001'.
        :param ip: Input IP
        :type ip: str

        :return: Formatted IP
        :rtype: str
        """
        return '.'.join(str(int(part)).zfill(3) for part in ip.split('.'))

    @staticmethod
    def parse_port(port):
        """
        Automatically change the input IP format like '05335'.
        :param port: Input IP
        :type port: str

        :return: Formatted IP
        :rtype: str
        """
        return str(int(port)).zfill(5)
