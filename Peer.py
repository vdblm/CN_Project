import warnings

from Stream import Stream
from Packet import Packet, PacketFactory
from UserInterface import UserInterface
from tools.NetworkGraph import NetworkGraph
from tools.Node import Node
import time
import threading

"""
    Peer is our main object in this project.
    In this network Peers will connect together to make a tree graph.
    This network is not completely decentralised but will show you some real-world challenges in Peer to Peer networks.
    
"""
import logging

logging.basicConfig(format='%(asctime)s %(message)s')


class Peer:
    def __init__(self, server_ip, server_port, is_root=False, root_address=None):
        """
        The Peer object constructor.

        Code design suggestions:
            1. Initialise a Stream object for our Peer.
            2. Initialise a PacketFactory object.
            3. Initialise our UserInterface for interaction with user commandline.
            4. Initialise a Thread for handling reunion daemon.

        Warnings:
            1. For root Peer, we need a NetworkGraph object.
            2. In root Peer, start reunion daemon as soon as possible.
            3. In client Peer, we need to connect to the root of the network, Don't forget to set this connection
               as a register_connection.


        :param server_ip: Server IP address for this Peer that should be pass to Stream.
        :param server_port: Server Port address for this Peer that should be pass to Stream.
        :param is_root: Specify that is this Peer root or not.
        :param root_address: Root IP/Port address if we are a client.

        :type server_ip: str
        :type server_port: int
        :type is_root: bool
        :type root_address: tuple
        """
        self.stream = Stream(server_ip, server_port)

        self.packet_factory = PacketFactory()

        self.user_interface = UserInterface()
        self.start_user_interface()

        self.is_root = is_root
        self.address = self.stream.get_server_address()
        if is_root:
            self.root_address = self.address
        else:
            self.root_address = (Node.parse_ip(root_address[0]), Node.parse_port(root_address[1]))

        self.parent_address = None

        self.reunion_daemon = threading.Thread(target=self.run_reunion_daemon)
        if is_root:
            # dict, {peer_address: time}
            self.peer_last_reunion_hello_time = {}
            self.network_graph = NetworkGraph(self.address)
            self.reunion_daemon.start()

        else:
            self.last_sent_reunion_time = None
            self.reunion_mode = 'accept'
            # the maximum depth is 8
            self.time_interval = 8 * 2 * 2 + 4
            self.reunion_failed = False
            self.first_advertise_response = True

    # Done
    def start_user_interface(self):
        """
        For starting UserInterface thread.

        :return:
        """
        self.user_interface.start()

    # Done#TODO warning. may run reunion multiple times
    def handle_user_interface_buffer(self):
        """
        In every interval, we should parse user command that buffered from our UserInterface.
        All of the valid commands are listed below:
            1. Register:  With this command, the client send a Register Request packet to the root of the network.
            2. Advertise: Send an Advertise Request to the root of the network for finding first hope.
            3. SendMessage: The following string will be added to a new Message packet and broadcast through the network.

        Warnings:
            1. Ignore irregular commands from the user.
            2. Don't forget to clear our UserInterface buffer.
        :return:
        """
        if self.is_root:
            self.user_interface.buffer.clear()
            return

        for command in self.user_interface.buffer:
            if command == 'Register':
                if not self.is_root:
                    pck = self.packet_factory.new_register_packet('REQ', self.address, address=self.address)
                    self.stream.add_node(self.root_address, set_register_connection=True)
                    self.stream.add_message_to_out_buff(self.root_address, pck.get_buf(), is_register=True)
                else:
                    logging.warning('root and register request??')
            elif command == 'Advertise':
                if not self.is_root:
                    pck = self.packet_factory.new_advertise_packet(type='REQ', source_server_address=self.address)
                    # TODO what to do if there is no node with root address?
                    self.stream.add_message_to_out_buff(self.root_address, pck.get_buf(), is_register=True)

            elif len(command.split(' ')) == 2 and command.split(' ')[0] == 'SendMessage':
                pck = self.packet_factory.new_message_packet(command.split(' ')[1], self.address)
                self.send_broadcast_packet(pck)
            else:
                logging.warning('Incorrect command')

        self.user_interface.buffer.clear()

    # Done
    def run(self):
        """
        The main loop of the program.

        Code design suggestions:
            1. Parse server in_buf of the stream.
            2. Handle all packets were received from our Stream server.
            3. Parse user_interface_buffer to make message packets.
            4. Send packets stored in nodes buffer of our Stream object.
            5. ** sleep the current thread for 2 seconds **

        Warnings:
            1. At first check reunion daemon condition; Maybe we have a problem in this time
               and so we should hold any actions until Reunion acceptance.
            2. In every situation checkout Advertise Response packets; even is Reunion in failure mode or not

        :return:
        """
        while True:
            if not self.is_root and self.reunion_failed:
                # just receive advertise responses and send advertise messages
                # do we need to clear buffer when reunion failed? yes. just for the advertise responses
                removed_bufs = []
                for buf in self.stream.read_in_buf():
                    pck = self.packet_factory.parse_buffer(buf)
                    if pck is None:
                        continue
                    if pck.get_type() == 2 and pck.get_body()[0:3] == 'RES':
                        # handle the advertise packet
                        self.handle_packet(pck)
                        removed_bufs.append(buf)
                [self.stream._server_in_buf.remove(removed_buf) for removed_buf in removed_bufs]

                for command in self.user_interface.buffer:
                    if command == 'Advertise':
                        pck = self.packet_factory.new_advertise_packet(type='REQ', source_server_address=self.address)
                        # TODO what to do if there is no node with root address?
                        self.stream.add_message_to_out_buff(self.root_address, pck.get_buf(), is_register=True)

                self.stream.send_out_buf_messages(only_register=True)
            else:
                # do regularly
                for buf in self.stream.read_in_buf():
                    pck = self.packet_factory.parse_buffer(buf)
                    if pck is None:
                        continue
                    self.handle_packet(pck)
                self.handle_user_interface_buffer()
                self.stream.send_out_buf_messages()
                self.stream.clear_in_buff()
            # sleep for 2 secs
            time.sleep(2)

    def run_reunion_daemon(self):
        """SendMessage: The following string will be added to a new Message packet and broadcast through the network.

        In this function, we will handle all Reunion actions.

        Code design suggestions:
            1. Check if we are the network root or not; The actions are identical.
            2. If it's the root Peer, in every interval check the latest Reunion packet arrival time from every node;
               If time is over for the node turn it off (Maybe you need to remove it from our NetworkGraph).
            3. If it's a non-root peer split the actions by considering whether we are waiting for Reunion Hello Back
               Packet or it's the time to send new Reunion Hello packet.

        Warnings:
            1. If we are the root of the network in the situation that we want to turn a node off, make sure that you will not
               advertise the nodes sub-tree in our GraphNode.
            2. If we are a non-root Peer, save the time when you have sent your last Reunion Hello packet; You need this
               time for checking whether the Reunion was failed or not.
            3. For choosing time intervals you should wait until Reunion Hello or Reunion Hello Back arrival,
               pay attention that our NetworkGraph depth will not be bigger than 8. (Do not forget main loop sleep time)
            4. Suppose that you are a non-root Peer and Reunion was failed, In this time you should make a new Advertise
               Request packet and send it through your register_connection to the root; Don't forget to send this packet
               here, because in the Reunion Failure mode our main loop will not work properly and everything will be got stock!

        :return:
        """
        while True:
            t = time.time()
            if self.is_root:
                removed_clients = []
                for client_address in self.peer_last_reunion_hello_time.keys():
                    # TODO calculate expected time of each client
                    # wait_time = (self.network_graph.get_node_depth(client_address) + 1) * 2
                    wait_time = 20
                    if int(t - self.peer_last_reunion_hello_time[client_address]) > wait_time:
                        # client time is over.
                        logging.warning('reunion failed from ' + str(client_address))
                        # TODO remove client from the network_graph and turn off its subtree
                        self.network_graph.remove_node(client_address)
                        # TODO remove from peer last reunion dict
                        removed_clients.append(client_address)
                # removing
                [self.peer_last_reunion_hello_time.pop(client_address) for client_address in removed_clients]

            else:
                if self.reunion_mode == 'pending':
                    if int(t - self.last_sent_reunion_time) > self.time_interval:
                        # time_out. need to send advertise again
                        logging.warning('reunion back failed')
                        pck = self.packet_factory.new_advertise_packet(type='REQ', source_server_address=self.address)
                        self.stream.add_message_to_out_buff(self.root_address, pck.get_buf(), is_register=True)
                        # self.stream.send_out_buf_messages(only_register=True)
                        self.reunion_failed = True
                    # TODO what to do when pending and it's not failed
                else:
                    self.reunion_failed = False
                    # send reunion hello
                    self.last_sent_reunion_time = t
                    self.reunion_mode = 'pending'
                    pck = self.packet_factory.new_reunion_packet(type='REQ', source_address=self.address,
                                                                 nodes_array=[self.address])
                    self.stream.add_message_to_out_buff(self.parent_address, pck.get_buf())

            # sleep for 4 seconds
            time.sleep(4)

    # Done
    def send_broadcast_packet(self, broadcast_packet):
        """

        For setting broadcast packets buffer into Nodes out_buff.

        Warnings:
            1. Don't send Message packets through register_connections.

        :param broadcast_packet: The packet that should be broadcast through the network.
        :type broadcast_packet: Packet

        :return:
        """
        for node_address in self.stream.nodes:
            self.stream.add_message_to_out_buff(node_address, broadcast_packet.get_buf())

    # Done
    def handle_packet(self, packet):
        """

        This function act as a wrapper for other handle_###_packet methods to handle the packet.

        Code design suggestion:
            1. It's better to check packet validation right now; For example Validation of the packet length.

        :param packet: The arrived packet that should be handled.

        :type packet Packet

        """

        # packet validation TODO do more?
        if len(packet.get_body()) != packet.get_length():
            logging.warning('packet length is not correct')
            return
        if packet.get_type() == 1:
            self.__handle_register_packet(packet)
        elif packet.get_type() == 2:
            self.__handle_advertise_packet(packet)
        elif packet.get_type() == 3:
            self.__handle_join_packet(packet)
        elif packet.get_type() == 4:
            self.__handle_message_packet(packet)
        elif packet.get_type() == 5:
            self.__handle_reunion_packet(packet)

    # Done
    def __check_registered(self, source_address):
        """
        If the Peer is the root of the network we need to find that is a node registered or not.

        :param source_address: Unknown IP/Port address.
        :type source_address: tuple

        :rtype: bool
        """

        # return True when it is registered
        node = self.stream.get_node_by_server(source_address[0], source_address[1], is_register=True)
        if node is None:
            return False
        return True

    # Done
    def __handle_advertise_packet(self, packet):
        """
        For advertising peers in the network, It is peer discovery message.

        Request:
            We should act as the root of the network and reply with a neighbour address in a new Advertise Response packet.

        Response:
            When an Advertise Response packet type arrived we should update our parent peer and send a Join packet to the
            new parent.

        Code design suggestion:
            1. Start the Reunion daemon thread when the first Advertise Response packet received.
            2. When an Advertise Response message arrived, make a new Join packet immediately for the advertised address.

        Warnings:
            1. Don't forget to ignore Advertise Request packets when you are a non-root peer.
            2. The addresses which still haven't registered to the network can not request any peer discovery message.
            3. Maybe it's not the first time that the source of the packet sends Advertise Request message. This will happen
               in rare situations like Reunion Failure. Pay attention, don't advertise the address to the packet sender
               sub-tree.
            4. When an Advertise Response packet arrived update our Peer parent for sending Reunion Packets.

        :param packet: Arrived register packet

        :type packet Packet

        :return:
        """
        # check if type of the packet is request
        if packet.get_body()[0:3] == 'REQ':
            if not self.is_root:
                logging.warning('received a request advertise packet on a non-root peer')
            else:
                if not self.__check_registered(packet.get_source_server_address()):
                    logging.warning(
                        'not registered node wants to advertise, node address: ' + str(
                            packet.get_source_server_address()))
                    return

                logging.warning('advertise request received from: ' + str(packet.get_source_server_address()))
                # find the neighbour
                neighbour_node = self.__get_neighbour(packet.get_source_server_address())
                # add the node to its networkgraph
                node = self.network_graph.find_node(packet.get_source_server_ip(), packet.get_source_server_port())
                if node is not None:
                    self.network_graph.turn_on_node(node.address, sub_tree=True)
                    node.set_parent(neighbour_node)
                else:
                    self.network_graph.add_node(packet.get_source_server_ip(), packet.get_source_server_port(),
                                                neighbour_node.address)

                pck = self.packet_factory.new_advertise_packet(type='RES', source_server_address=self.address,
                                                               neighbour=neighbour_node.address)
                # send through register node
                self.stream.add_message_to_out_buff(packet.get_source_server_address(), pck.get_buf(), is_register=True)

                # add to peer last reunion hello time TODO im not sure of this
                self.peer_last_reunion_hello_time[packet.get_source_server_address()] = time.time()

        elif packet.get_body()[0:3] == 'RES':
            if self.is_root:
                logging.warning('root received advertise response')
                return
            if packet.get_source_server_address() != self.root_address:
                logging.warning('received advertise response from non-root peer')
                return

            neighbour_ip = packet.get_body()[3:18]
            neighbour_port = packet.get_body()[18:23]
            # update parent
            self.parent_address = (neighbour_ip, neighbour_port)

            logging.warning('advertise response received. the neighbour is: ' + str(self.parent_address))
            # Add parent node to the stream
            self.stream.add_node(self.parent_address)

            # make a join packet
            pck = self.packet_factory.new_join_packet(self.address)
            self.stream.add_message_to_out_buff(self.parent_address, pck.get_buf())

            # TODO im not sure of this
            self.reunion_failed = False

            # TODO im not fucking sure of this
            self.reunion_mode = 'accept'
            # start reunion daemon
            if self.first_advertise_response:
                self.reunion_daemon.start()
                self.first_advertise_response = False
        else:
            logging.warning('undefined packet received')

    # Done
    def __handle_register_packet(self, packet):
        """
        For registration a new node to the network at first we should make a Node with stream.add_node for'sender' and
        save it.

        Code design suggestion:
            1.For checking whether an address is registered since now or not you can use SemiNode object except Node.

        Warnings:
            1. Don't forget to ignore Register Request packets when you are a non-root peer.

        :param packet: Arrived register packet
        :type packet Packet
        :return:
        """
        if self.is_root:
            if packet.get_body()[0:3] != 'REQ':
                logging.warning('response register packet arrived at root:)')
                return
            ip = packet.get_body()[3:18]
            port = packet.get_body()[18:23]
            sender_address = (ip, port)
            if not self.__check_registered(sender_address):
                logging.warning('Register Request received from: ' + str(packet.get_source_server_address()))
                self.stream.add_node(sender_address, set_register_connection=True)
                pck = self.packet_factory.new_register_packet(type='RES', source_server_address=self.address)
                self.stream.add_message_to_out_buff(address=sender_address,
                                                    message=pck.get_buf(), is_register=True)
            else:
                logging.warning('an already registered node wants to register again')

        else:
            if packet.get_body()[0:3] == 'REQ':
                logging.warning('register request arrived at a non-root peer')
            elif packet.get_body()[0:3] == 'RES' and packet.get_body()[3:6] == 'ACK':
                logging.warning('Register response received at ' + str(self.address))
            else:
                logging.warning('incorrect register response received at ' + str(self.address))

    # Done
    def __check_neighbour(self, address):
        """
        It checks is the address in our neighbours array or not.

        :param address: Unknown address

        :type address: tuple

        :return: Whether is address in our neighbours or not.
        :rtype: bool
        """
        node = self.stream.get_node_by_server(address[0], address[1])
        if node is None:
            return False
        return True

    # Done
    def __handle_message_packet(self, packet):
        """
        Only broadcast message to the other nodes.

        Warnings:
            1. Do not forget to ignore messages from unknown sources.
            2. Make sure that you are not sending a message to a register_connection.

        :param packet: Arrived message packet

        :type packet Packet

        :return:
        """
        if not self.__check_neighbour(packet.get_source_server_address()):
            logging.warning('received packet from unknown source')
            return

        pck = self.packet_factory.new_message_packet(packet.get_body(), self.address)
        logging.warning('message ' + packet.get_body() + ' received from ' + str(packet.get_source_server_address()))
        for node_address in self.stream.nodes:
            if node_address != packet.get_source_server_address():
                logging.warning('message ' + packet.get_body() + ' sent to ' + str(node_address))
                self.stream.add_message_to_out_buff(node_address, pck.get_buf())

    # Done
    def __handle_reunion_packet(self, packet):
        """
        In this function we should handle Reunion packet was just arrived.

        Reunion Hello:
            If you are root Peer you should answer with a new Reunion Hello Back packet.
            At first extract all addresses in the packet body and append them in descending order to the new packet.
            You should send the new packet to the first address in the arrived packet.
            If you are a non-root Peer append your IP/Port address to the end of the packet and send it to your parent.

        Reunion Hello Back:
            Check that you are the end node or not; If not only remove your IP/Port address and send the packet to the next
            address, otherwise you received your response from the root and everything is fine.

        Warnings:
            1. Every time adding or removing an address from packet don't forget to update Entity Number field.
            2. If you are the root, update last Reunion Hello arrival packet from the sender node and turn it on.
            3. If you are the end node, update your Reunion mode from pending to acceptance.


        :param packet: Arrived reunion packet
        :return:
        """
        try:
            body = packet.get_body()
            nodes_array = []
            i = 5
            while i < len(body):
                nodes_array.append((body[i:(i + 15)], body[(i + 15):(i + 20)]))
                i += 20
        except:
            logging.warning('reunion packet has invalid body (nodes array is not correct)')
            return

        # reunion hello
        t = time.time()
        if packet.get_body()[0:3] == 'REQ':
            if self.is_root:
                # Answer reunion hello back
                self.peer_last_reunion_hello_time[nodes_array[0]] = t
                self.network_graph.turn_on_node(nodes_array[0])
                nodes_array.reverse()
                pck = self.packet_factory.new_reunion_packet(type='RES', source_address=self.address,
                                                             nodes_array=nodes_array)
                neighbour_addr = nodes_array[0]
                self.stream.add_message_to_out_buff(neighbour_addr, pck.get_buf())

            else:
                # add your ip/port
                nodes_array.append(self.address)
                pck = self.packet_factory.new_reunion_packet(type='REQ', source_address=self.address,
                                                             nodes_array=nodes_array)
                self.stream.add_message_to_out_buff(self.parent_address, pck.get_buf())

        # reunion hello back
        elif packet.get_body()[0:3] == 'RES':
            if nodes_array[0] != self.address:
                logging.warning(
                    'the last address in the reunion back packet body and the receiver address are not the same')
                return
            if len(nodes_array) == 1:
                # the end client
                self.reunion_mode = 'accept'
                # self.time_interval = t - self.last_sent_reunion_time
                # self.last_sent_reunion_time = t
            elif len(nodes_array) > 1:
                # the middle client
                pck = self.packet_factory.new_reunion_packet(type='RES', source_address=self.address,
                                                             nodes_array=nodes_array[1:])
                self.stream.add_message_to_out_buff(nodes_array[1], pck.get_buf())
            else:
                logging.warning('the reunion back packet has no nodes array in its body')

    # Done
    def __handle_join_packet(self, packet):
        """
        When a Join packet received we should add a new node to our nodes array.
        In reality, there is a security level that forbids joining every node to our network.

        :param packet: Arrived register packet.


        :type packet Packet

        :return:
        """
        if self.stream.get_node_by_server(packet.get_source_server_ip(), packet.get_source_server_port()) is None:
            self.stream.add_node(packet.get_source_server_address())
            # Do nothing else??
            logging.warning('join message received from: ' + str(packet.get_source_server_address()))
        else:
            logging.warning('an already joined peer wants to join again, the address is: ' + str(
                packet.get_source_server_address()))

    # Done
    def __get_neighbour(self, sender):
        """
        Finds the best neighbour for the 'sender' from the network_nodes array.
        This function only will call when you are a root peer.

        Code design suggestion:
            1. Use your NetworkGraph find_live_node to find the best neighbour.

        :param sender: Sender of the packet
        :return: The specified neighbour for the sender; The format is like ('192.168.001.001', '05335').
        """
        node = self.network_graph.find_live_node(sender)
        if node is not None:
            return node
        else:
            logging.warning('There is no neighbour node for the sender')
            return None
