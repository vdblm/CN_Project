from Peer import Peer

if __name__ == "__main__":
    server = Peer("127.0.0.1", 5022, is_root=True)
    server.run()

    # client = Peer("127.0.0.1", "Insert Port as Int", is_root=False,
    #               root_address=("Insert IP Address", "Insert Port as Int"))
