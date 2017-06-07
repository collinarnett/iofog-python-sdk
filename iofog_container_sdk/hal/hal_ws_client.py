import threading
import json
from struct import pack
from ws4py.client.threadedclient import WebSocketClient
from constants import *


class WSClient(WebSocketClient):
    def __init__(self, config, handler):
        self.handler = handler
        self.config = config
        self.ws_url = WS_REQUEST_URL_PATTERN.format(HOST, HAL_WS_PORT) + HAL_USB_TO_SERIAL_BASE_PATH + \
                      config[HAL_USB_TO_SERIAL_PORT_PROPERTY_NAME]
        self.worker = None
        self.is_opened = False
        super(WSClient, self).__init__(url=self.ws_url)

    def opened(self):
        print('Socket connection opened')
        self._send_open_connection()

    def closed(self, code, reason=None):
        print "Closed down", code, reason
        if code == HAL_WS_CLOSE_FRAME_STATUS_EXCEPTION:
            self.close(code=HAL_WS_CLOSE_FRAME_STATUS_NORMAL, reason='Client closed successfully.')
        self.worker = None
        self.is_opened = False
        self.handler.connection_closed(code, reason)

    def _send_open_connection(self):
        config_package = bytearray()
        config_package.extend(json.dumps(self.config))
        package = bytearray([HAL_WS_OPEN_CONNECTION_OPCODE])
        package.extend(pack('>I', len(config_package)))
        package += config_package
        self.send(package, binary=True)
        return

    def connect(self):
        print('Starting connection via ws')
        self.worker = threading.Thread(target=self._serve_, name='WS Server')
        self.worker.start()
        return

    def _serve_(self):
        print('Starting serving on ws')
        try:
            super(WSClient, self).connect()
        except Exception, e:
            print('Error connecting to socket: {}'.format(e))
        self.run_forever()
        # print('Loop exited')

    def received_message(self, message):
        if self.handler:
            if message:
                if message.is_binary:
                    data = bytearray(message.data)
                    opcode = data[0]
                    if opcode == HAL_WS_CONNECTION_OPENED_OPCODE:
                        print('Connection opened to Device')
                        self.is_opened = True
                        self.handler.connection_opened()
                    elif opcode == HAL_WS_GOT_DATA_OPCODE:
                        self.handler.got_data(data[5:])
                else:
                    print('Message is not binary:' + str(message.data))
            else:
                print('Empty message')
        else:
            print('No handler specified yet to handle messages')

    def send_data(self, data):
        package = bytearray([HAL_WS_SEND_DATA_OPCODE])
        package.extend(pack('>I', len(data)))
        package += data
        print('Sending data: {}'.format(package))
        self.send(package, binary=True)
        return

    def send_close_frame(self):
        # TODO: check if conn open and close it with code and reason
        # Maybe standard function will be enough
        self.is_opened = False
        self.worker = None
        self.close(code=1000, reason='Client wants to close connection to device.')
        return

    def is_opened(self):
        return self.is_opened
