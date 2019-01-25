from Peer import Peer

if __name__ == "__main__":
    client = Peer("127.0.0.1", 17003, is_root=False,
                  root_address=("127.0.0.1", 5000))
    client.run()
