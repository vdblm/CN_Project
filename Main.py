from Peer import Peer

if __name__ == "__main__":
    server = Peer("127.0.0.1", 5000, is_root=True)
    server.run()
