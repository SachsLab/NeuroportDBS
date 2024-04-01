import time

import zmq


topic_port = {
    "procedure_settings": 60001,
    "snippet_status": 60002,
    "channel_select": 60003,
    "features": 60004,
    "ddu": 60005,
}

context = zmq.Context()
sub_socks = {}

for topic, port in topic_port.items():
    sub_socks[topic] = context.socket(zmq.SUB)
    sub_socks[topic].connect(f"tcp://localhost:{port}")
    sub_socks[topic].setsockopt_string(zmq.SUBSCRIBE, topic)


try:
    while True:
        for topic, sock in sub_socks.items():
            try:
                recv_msg = sock.recv_string(flags=zmq.NOBLOCK)[len(topic) + 1:]
                print(topic, recv_msg)
            except zmq.ZMQError:
                time.sleep(0.1)
except KeyboardInterrupt:
    pass
