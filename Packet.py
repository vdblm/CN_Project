"""

    This is the format of packets in our network:
    


                                                **  NEW Packet Format  **
     __________________________________________________________________________________________________________________
    |           Version(2 Bytes)         |         Type(2 Bytes)         |           Length(Long int/4 Bytes)          |
    |------------------------------------------------------------------------------------------------------------------|
    |                                            Source Server IP(8 Bytes)                                             |
    |------------------------------------------------------------------------------------------------------------------|
    |                                           Source Server Port(4 Bytes)                                            |
    |------------------------------------------------------------------------------------------------------------------|
    |                                                    ..........                                                    |
    |                                                       BODY                                                       |
    |                                                    ..........                                                    |
    |__________________________________________________________________________________________________________________|

    Version:
        For now version is 1
    
    Type:
        1: Register
        2: Advertise
        3: Join
        4: Message
        5: Reunion
                e.g: type = '2' => Advertise packet.
    Length:
        This field shows the character numbers for Body of the packet.

    Server IP/Port:
        We need this field for response packet in non-blocking mode.



    ***** For example: ******

    version = 1                 b'\x00\x01'
    type = 4                    b'\x00\x04'
    length = 12                 b'\x00\x00\x00\x0c'
    ip = '192.168.001.001'      b'\x00\xc0\x00\xa8\x00\x01\x00\x01'
    port = '65000'              b'\x00\x00\\xfd\xe8'
    Body = 'Hello World!'       b'Hello World!'

    Bytes = b'\x00\x01\x00\x04\x00\x00\x00\x0c\x00\xc0\x00\xa8\x00\x01\x00\x01\x00\x00\xfd\xe8Hello World!'




    Packet descriptions:
    
        Register:
            Request:
        
                                 ** Body Format **
                 ________________________________________________
                |                  REQ (3 Chars)                 |
                |------------------------------------------------|
                |                  IP (15 Chars)                 |
                |------------------------------------------------|
                |                 Port (5 Chars)                 |
                |________________________________________________|
                
                For sending IP/Port of the current node to the root to ask if it can register to network or not.

            Response:
        
                                 ** Body Format **
                 _________________________________________________
                |                  RES (3 Chars)                  |
                |-------------------------------------------------|
                |                  ACK (3 Chars)                  |
                |_________________________________________________|
                
                For now only should just send an 'ACK' from the root to inform a node that it
                has been registered in the root if the 'Register Request' was successful.
                
        Advertise:
            Request:
            
                                ** Body Format **
                 ________________________________________________
                |                  REQ (3 Chars)                 |
                |________________________________________________|
                
                Nodes for finding the IP/Port of their neighbour peer must send this packet to the root.

            Response:

                                ** Packet Format **
                 ________________________________________________
                |                RES(3 Chars)                    |
                |------------------------------------------------|
                |              Server IP (15 Chars)              |
                |------------------------------------------------|
                |             Server Port (5 Chars)              |
                |________________________________________________|
                
                Root will response Advertise Request packet with sending IP/Port of the requester peer in this packet.
                
        Join:

                                ** Body Format **
                 ________________________________________________
                |                 JOIN (4 Chars)                 |
                |________________________________________________|
            
            New node after getting Advertise Response from root must send this packet to the specified peer
            to tell him that they should connect together; When receiving this packet we should update our
            Client Dictionary in the Stream object.


            
        Message:
                                ** Body Format **
                 ________________________________________________
                |             Message (#Length Chars)            |
                |________________________________________________|

            The message that want to broadcast to whole network. Right now this type only includes a plain text.
        
        Reunion:
            Hello:
        
                                ** Body Format **
                 ________________________________________________
                |                  REQ (3 Chars)                 |
                |------------------------------------------------|
                |           Number of Entries (2 Chars)          |
                |------------------------------------------------|
                |                 IP0 (15 Chars)                 |
                |------------------------------------------------|
                |                Port0 (5 Chars)                 |
                |------------------------------------------------|
                |                 IP1 (15 Chars)                 |
                |------------------------------------------------|
                |                Port1 (5 Chars)                 |
                |------------------------------------------------|
                |                     ...                        |
                |------------------------------------------------|
                |                 IPN (15 Chars)                 |
                |------------------------------------------------|
                |                PortN (5 Chars)                 |
                |________________________________________________|
                
                In every interval (for now 20 seconds) peers must send this message to the root.
                Every other peer that received this packet should append their (IP, port) to
                the packet and update Length.

            Hello Back:
        
                                    ** Body Format **
                 ________________________________________________
                |                  RES (3 Chars)                 |
                |------------------------------------------------|
                |           Number of Entries (2 Chars)          |
                |------------------------------------------------|
                |                 IPN (15 Chars)                 |
                |------------------------------------------------|
                |                PortN (5 Chars)                 |
                |------------------------------------------------|
                |                     ...                        |
                |------------------------------------------------|
                |                 IP1 (15 Chars)                 |
                |------------------------------------------------|
                |                Port1 (5 Chars)                 |
                |------------------------------------------------|
                |                 IP0 (15 Chars)                 |
                |------------------------------------------------|
                |                Port0 (5 Chars)                 |
                |________________________________________________|

                Root in an answer to the Reunion Hello message will send this packet to the target node.
                In this packet, all the nodes (IP, port) exist in order by path traversal to target.
            
    
"""
import unittest
import warnings
from struct import *

from tools.Node import Node

import logging

logging.basicConfig(format='%(asctime)s %(message)s')


class Packet:
    def __init__(self, buf):
        """
        The decoded buffer should convert to a new packet.

        :param buf: Input buffer was just decoded.
        :type buf: list
        """
        self.buf = buf

    def get_header(self):
        """

        :return: Packet header
        :rtype: str
        """
        pass

    def get_version(self):
        """

        :return: Packet Version
        :rtype: int
        """
        return self.buf[0]

    def get_type(self):
        """

        :return: Packet type
        :rtype: int
        """
        return self.buf[1]

    def get_length(self):
        """

        :return: Packet length
        :rtype: int
        """
        return self.buf[2]

    def get_body(self):
        """

        :return: Packet body
        :rtype: str
        """
        return self.buf[5]

    def get_buf(self):
        """
        In this function, we will make our final buffer that represents the Packet with the Struct class methods.

        :return The parsed packet to the network format.
        :rtype: bytearray
        """
        ip_splits = self.get_source_server_ip().split(".")

        return pack('>HHIHHHHI', self.get_version(), self.get_type(), self.get_length(),
                    int(ip_splits[0]), int(ip_splits[1]), int(ip_splits[2]), int(ip_splits[3]),
                    int(self.get_source_server_port())) + str.encode(self.get_body())

    def get_source_server_ip(self):
        """

        :return: Server IP address for the sender of the packet.
        :rtype: str
        """
        return self.buf[3]

    def get_source_server_port(self):
        """

        :return: Server Port address for the sender of the packet.
        :rtype: str
        """
        return self.buf[4]

    def get_source_server_address(self):
        """

        :return: Server address; The format is like ('192.168.001.001', '05335').
        :rtype: tuple
        """
        ret = (self.get_source_server_ip(), self.get_source_server_port())
        return ret


class PacketFactory:
    """
    This class is only for making Packet objects.
    """

    @staticmethod
    def parse_buffer(buf):
        """
        In this function we will make a new Packet from input buffer with struct class methods.

        :param buf: The buffer that should be parse to a validate packet format

        :return new packet
        :rtype: Packet

        """
        try:
            version = buf[0:2]
            typ = buf[2:4]
            length = buf[4:8]
            ip = buf[8:16]
            port = buf[16:20]
            body = buf[20:]
            version = unpack_from('>H', version)[0]
            type = unpack_from('>H', typ)[0]
            length = unpack_from('>I', length)[0]
            ip_tuple = unpack_from('>HHHH', ip)
            ip = ""
            for t in ip_tuple:
                ip += '.' + str(t)
            ip = ip[1:]
            port = str(unpack_from('>I', port)[0])
            ip = Node.parse_ip(ip)
            port = Node.parse_port(port)
            body = body.decode("utf-8")

            pck = [version, type, length, ip, port, body]

            return Packet(pck)
        except:
            # any error means the packet's format was wrong
            logging.warning('received packet format was wrong')
            return None

    @staticmethod
    def new_reunion_packet(type, source_address, nodes_array):
        """
        :param type: Reunion Hello (REQ) or Reunion Hello Back (RES)
        :param source_address: IP/Port address of the packet sender.
        :param nodes_array: [(ip0, port0), (ip1, port1), ...] It is the path to the 'destination'.

        :type type: str
        :type source_address: tuple
        :type nodes_array: list

        :return New reunion packet.
        :rtype Packet
        """

        # Don't add the source address to the nodes_array here!
        entries_number = str(len(nodes_array))
        if len(entries_number) == 1:
            entries_number = '0' + entries_number
        # We assume the order of nodes_array is handled in Peer
        body = type + entries_number
        for node in nodes_array:
            body += node[0] + str(node[1])

        length = len(body)
        # version is 1, type is 5 (reunion),
        return Packet([1, 5, length, source_address[0], source_address[1], body])

    @staticmethod
    def new_advertise_packet(type, source_server_address, neighbour=None):
        """
        :param type: Type of Advertise packet
        :param source_server_address Server address of the packet sender.
        :param neighbour: The neighbour for advertise response packet; The format is like ('192.168.001.001', '05335').

        :type type: str
        :type source_server_address: tuple
        :type neighbour: tuple

        :return New advertise packet.
        :rtype Packet

        """
        if type == 'REQ':
            body = type
        elif type == 'RES':
            if neighbour is None:
                logging.warning('in advertise response, neighbour is None')
                return
            body = type + neighbour[0] + neighbour[1]
        else:
            logging.warning('Type was not correct')
            return

        # version is 1, type is 2 (advertise)
        return Packet([1, 2, len(body), source_server_address[0], source_server_address[1], body])

    @staticmethod
    def new_join_packet(source_server_address):
        """
        :param source_server_address: Server address of the packet sender.

        :type source_server_address: tuple

        :return New join packet.
        :rtype Packet

        """

        # type is 3 (join), len(body) is 4, body is 'JOIN'
        return Packet([1, 3, 4, source_server_address[0], source_server_address[1], 'JOIN'])

    @staticmethod
    def new_register_packet(type, source_server_address, address=(None, None)):
        """
        :param type: Type of Register packet
        :param source_server_address: Server address of the packet sender.
        :param address: If 'type' is 'request' we need an address; The format is like ('192.168.001.001', '05335').

        :type type: str
        :type source_server_address: tuple
        :type address: tuple

        :return New Register packet.
        :rtype Packet

        """
        if type == 'RES':
            body = type + 'ACK'
        elif type == 'REQ':
            if address is (None, None):
                logging.warning('in register request, address is None')
                return
            body = type + address[0] + address[1]
        else:
            logging.warning('Type was not correct')
            return

        # version is 1, type is 1 (register)
        return Packet([1, 1, len(body), source_server_address[0], source_server_address[1], body])

    @staticmethod
    def new_message_packet(message, source_server_address):
        """
        Packet for sending a broadcast message to the whole network.

        :param message: Our message
        :param source_server_address: Server address of the packet sender.

        :type message: str
        :type source_server_address: tuple

        :return: New Message packet.
        :rtype: Packet
        """
        # version is 1, type is 4 (message)
        return Packet([1, 4, len(message), source_server_address[0], source_server_address[1], message])


class TestPacketFactory(unittest.TestCase):

    def test_parse_buf(self):
        buf = b'\x00\x01\x00\x04\x00\x00\x00\x0c\x00\xc0\x00\xa8\x00\x01\x00\x01\x00\x00\xfd\xe8Hello World!'
        pck = PacketFactory.parse_buffer(buf)
        self.assertEqual(pck.get_buf(), buf)

    def test_new_reunion_packet(self):
        pck = PacketFactory.new_reunion_packet(type='REQ', source_address=('127.000.000.001', '31315'),
                                               nodes_array=[("127.000.000.001", '31315')])
        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x05\x00\x00\x00\x19\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00zSREQ01127.000.000.00131315')

        pck = PacketFactory.new_reunion_packet(type='RES', source_address=('127.000.000.001', '05356'),
                                               nodes_array=[("127.000.000.001", '31315')])

        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x05\x00\x00\x00\x19\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00\x14\xecRES01127.000.000.00131315')

    def test_new_advertise_packet(self):
        pck = PacketFactory.new_advertise_packet(type='REQ', source_server_address=("127.000.000.001", "31315"))
        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x02\x00\x00\x00\x03\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00zSREQ')

        pck = PacketFactory.new_advertise_packet(type='RES', source_server_address=("127.000.000.001", "05356"),
                                                 neighbour=("127.000.000.001", "05356"))
        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x02\x00\x00\x00\x17\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00\x14\xecRES127.000.000.00105356')

    def test_new_join_packet(self):
        pck = PacketFactory.new_join_packet(source_server_address=("127.000.000.001", "31315"))
        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x03\x00\x00\x00\x04\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00zSJOIN')

    def test_new_message_packet(self):
        pck = PacketFactory.new_message_packet('Hi', source_server_address=("127.000.000.001", "31315"))
        self.assertEqual(pck.get_buf(), b'\x00\x01\x00\x04\x00\x00\x00\x02\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00zSHi')

    def test_new_register_packet(self):
        pck = PacketFactory.new_register_packet('REQ', source_server_address=("127.000.000.001", "31315"),
                                                address=("127.000.000.001", "31315"))
        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x01\x00\x00\x00\x17\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00zSREQ127.000.000.00131315')

        pck = PacketFactory.new_register_packet('RES', source_server_address=("127.000.000.001", "05356"))
        self.assertEqual(pck.get_buf(),
                         b'\x00\x01\x00\x01\x00\x00\x00\x06\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00\x14\xecRESACK')
