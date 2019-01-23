import time
import warnings


class GraphNode:
    def __init__(self, address):
        """

        :param address: (ip, port)
        :type address: tuple

        """
        self.address = address
        self.children = []
        self.parent = None
        self.alive = True

    def set_parent(self, parent):
        self.parent = parent

    def set_address(self, new_address):
        self.address = new_address

    def __reset(self):
        # not sure
        self.parent = None
        self.children = []
        self.alive = True

    def add_child(self, child):
        self.children.append(child)


class NetworkGraph:
    def __init__(self, root):
        self.root = root
        root.alive = True
        self.nodes = [root]

    def find_live_node(self, sender):
        """
        Here we should find a neighbour for the sender.
        Best neighbour is the node who is nearest the root and has not more than one child.

        Code design suggestion:
            1. Do a BFS algorithm to find the target.

        Warnings:
            1. Check whether there is sender node in our NetworkGraph or not; if exist do not return sender node or
               any other nodes in it's sub-tree.

        :param sender: The node address we want to find best neighbour for it.
        :type sender: tuple

        :return: Best neighbour for sender.
        :rtype: GraphNode
        """
        to_visit = [self.root]
        visited = set()
        l = len(to_visit)
        while l > 0:
            node = to_visit[0]
            to_visit = to_visit[1:]
            if node.address == sender:
                visited.add(node)
                continue
            if node.alive and len(node.children) < 2:
                return node
            visited.add(node)
            for child in node.children:
                if child not in visited:
                    to_visit.append(child)
            l = len(to_visit)
        return None

    def find_node(self, ip, port):
        address = (ip, port)
        for node in self.nodes:
            if node.address == address:
                return node
        return None

    def turn_on_node(self, node_address):
        node = self.find_node(node_address[0], node_address[1])
        node.alive = True

    def turn_off_node(self, node_address):
        node = self.find_node(node_address[0], node_address[1])
        node.alive = False

    def remove_node(self, node_address):
        node = self.find_node(node_address[0], node_address[1])
        if node.parent is not None:
            node.parent.children.remove(node)
        self.remove_subtree(node)

    def remove_subtree(self, node):
        for child in node.children:
            self.remove_subtree(child)
        self.nodes.remove(node)

    def add_node(self, ip, port, father_address):
        """
        Add a new node with node_address if it does not exist in our NetworkGraph and set its father.

        Warnings:
            1. Don't forget to set the new node as one of the father_address children.
            2. Before using this function make sure that there is a node which has father_address.

        :param ip: IP address of the new node.
        :param port: Port of the new node.
        :param father_address: Father address of the new node

        :type ip: str
        :type port: int
        :type father_address: tuple


        :return:
        """
        father_node = self.find_node(father_address[0], father_address[1])
        if father_node is None:
            warnings.warn("There is no node with father_address")
        elif self.find_node(ip, port) is None:
            node = GraphNode(address=(ip, port))
            node.set_parent(father_node)
            father_node.add_child(node)
            self.nodes.append(node)


import unittest


class TestNetworkGraph(unittest.TestCase):

    def initiate(self):
        root_address = ('192.168.1.1', 2005)
        root = GraphNode(address=root_address)
        ng = NetworkGraph(root=root)
        ng.add_node(ip='192.168.1.2', port=125, father_address=root_address)
        ng.add_node(ip='192.168.1.3', port=125, father_address=root_address)
        ng.add_node(ip='192.168.1.4', port=125, father_address=('192.168.1.2', 125))
        ng.add_node(ip='192.168.1.5', port=125, father_address=('192.168.1.2', 125))
        return ng

    def test_find_live_node_one(self):
        ng = self.initiate()
        node = ng.find_live_node(('192.168.1.6', 125))
        self.assertEqual(node.address, ('192.168.1.3', 125))

    def test_find_live_node_two(self):
        ng = self.initiate()
        node = ng.find_live_node(('192.168.1.3', 125))
        self.assertEqual(node.address, ('192.168.1.4', 125))

    def test_remove_node(self):
        ng = self.initiate()
        ng.remove_node(('192.168.1.2', 125))
        self.assertEqual(len(ng.nodes), 2)