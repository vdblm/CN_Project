import warnings

from tools.simpletcp.tcpserver import TCPServer

from tools.Node import Node
import threading


class Stream:

    def __init__(self, ip, port):
        """
        The Stream object constructor.

        Code design suggestion:
            1. Make a separate Thread for your TCPServer and start immediately.


        :param ip: 15 characters
        :param port: 5 characters
        """

        ip = Node.parse_ip(ip)
        port = Node.parse_port(port)

        self.server_address = (ip, port)
        self._server_in_buf = []

        # Dict for nodes {address: node object} and register nodes
        # address is (ip, port)
        self.nodes = {}
        self.register_nodes = {}

        def callback(address, queue, data):
            """
            The callback function will run when a new data received from server_buffer.

            :param address: Source address.
            :param queue: Response queue.
            :param data: The data received from the socket.
            :return:
            """
            queue.put(bytes('ACK', 'utf8'))
            self._server_in_buf.append(data)

        def tcp_server():
            server = TCPServer(ip, port, callback)
            server.run()

        tcp = threading.Thread(target=tcp_server)
        tcp.start()

    def get_server_address(self):
        """

        :return: Our TCPServer addresssend_broadcast_packet
        :rtype: tuple
        """
        return self.server_address

    def clear_in_buff(self):
        """
        Discard any data in TCPServer input buffer.

        :return:
        """
        self._server_in_buf.clear()

    def add_node(self, server_address, set_register_connection=False):
        """
        Will add new a node to our Stream.

        :param server_address: New node TCPServer address.
        :param set_register_connection: Shows that is this connection a register_connection or not.

        :type server_address: tuple
        :type set_register_connection: bool

        :return:
        """
        try:
            node = Node(server_address, set_register_connection)
            if set_register_connection:
                self.register_nodes[server_address] = node
            else:
                self.nodes[server_address] = node
        except:
            warnings.warn('node did not added')

    def remove_node(self, node):
        """
        Remove the node from our Stream.

        Warnings:
            1. Close the node after deletion.

        :param node: The node we want to remove.
        :type node: Node

        :return:
        """
        node.close()
        server_address = node.get_server_address()
        # remove the node from nodes dict
        if node.is_register:
            t = self.register_nodes.pop(server_address, None)
        else:
            t = self.nodes.pop(server_address, None)
        if t is None:
            warnings.warn(
                'wants to remove a non-existing node in the stream, address: ' + str(self.get_server_address()))

    def get_node_by_server(self, ip, port, is_register=False):
        """

        Will find the node that has IP/Port address of input.

        Warnings:
            1. Before comparing the address parse it to a standard format with Node.parse_### functions.

        :param ip: input address IP
        :param port: input address Port
        :param is_register: if the node is register node

        :return: The node that input address.
        :rtype: Node
        :rtype: bool
        """

        node_address = (Node.parse_ip(ip), Node.parse_port(port))
        if is_register:
            node = self.register_nodes.get(node_address)
        else:
            node = self.nodes.get(node_address)
        if node is None:
            warnings.warn(
                'node does not exit, node: ' + str(node_address) + ' stream address: ' + str(self.get_server_address()))
        return node

    def add_message_to_out_buff(self, address, message, is_register=False):
        """
        In this function, we will add the message to the output buffer of the node that has the input address.
        Later we should use send_out_buf_messages to send these buffers into their sockets.

        :param address: Node address that we want to send the message
        :param message: Message we want to send
        :param is_register: If the node is register

        Warnings:
            1. Check whether the node address is in our nodes or not.

        :return:
        """
        if is_register:
            node = self.register_nodes.get(address)
        else:
            node = self.nodes.get(address)
        if node is None:
            warnings.warn(
                "There is no node with this address: " + str(address) + " in Stream: " + str(self.get_server_address()))
        else:
            node.add_message_to_out_buff(message)

    def read_in_buf(self):
        """
        Only returns the input buffer of our TCPServer.

        :return: TCPServer input buffer.
        :rtype: list
        """
        return self._server_in_buf

    def _send_messages_to_node(self, node):
        """
        Send buffered messages to the 'node'

        Warnings:
            1. Insert an exception handler here; Maybe the node socket you want to send the message has turned off and
            you need to remove this node from stream nodes.

        :param node:
        :type node Node

        :return:
        """
        # TODO Im not sure of this
        try:
            node.send_message()
        except:
            warnings.warn('Node could not send message to dest peer. Maybe the dest peer is turned off')
            if node.is_register:
                self.register_nodes.pop(node.get_server_address(), None)
            else:
                self.nodes.pop(node.get_server_address(), None)

    def send_out_buf_messages(self, only_register=False):
        """
        In this function, we will send whole out buffers to their own clients.

        :return:
        """
        if only_register:
            for node in self.register_nodes.values():
                self._send_messages_to_node(node)
        else:
            for node in self.nodes.values():
                self._send_messages_to_node(node)
