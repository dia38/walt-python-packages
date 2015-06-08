#!/usr/bin/env python
import rpyc, os, sys, signal, threading
from walt.common.constants import WALT_SERVER_DAEMON_PORT

SERVER="localhost"

class ExposedStream(object):
    def __init__(self, stream):
        self.stream = stream
    def exposed_fileno(self):
        return self.stream.fileno()
    def exposed_readline(self, size=-1):
        return self.stream.readline(size)
    def exposed_write(self, s):
        self.stream.write(s)
    def exposed_flush(self):
        self.stream.flush()

# most of the functionality is provided at the server,
# of course. 
# but the client also exposes a few objects / features
# in the following class.
class WaltClientService(rpyc.Service):
    def __init__(self, *args, **kwargs):
        rpyc.Service.__init__(self, *args, **kwargs)
        self.exposed_stdin = ExposedStream(sys.stdin)
        self.exposed_stdout = ExposedStream(sys.stdout)
        self.exposed_stderr = ExposedStream(sys.stderr)

# in some cases we need a background thread that will handle
# RPyC events.
class BgRPyCThread(object):
    def __init__(self, conn):
        self.conn = conn
        self.thread = threading.Thread(target = self._bg_server)
        self.thread.setDaemon(True)
        self.active = True
        self.thread.start()
    def __del__(self):
        if self.active:
            self.stop()
    def _bg_server(self):
        try:
            while self.active:
                self.conn.serve()
        except Exception:
            if self.active:
                raise
    def stop(self):
        assert self.active
        self.active = False
        self.thread.join()
        self.conn = None

class ClientToServerLink:
    def __init__(self, bg_thread_enabled = False):
        self.bg_thread_enabled = bg_thread_enabled

    def __enter__(self):
        self.conn = rpyc.connect(
                SERVER,
                WALT_SERVER_DAEMON_PORT,
                service = WaltClientService)
        if self.bg_thread_enabled:
            self.bg_thread = BgRPyCThread(self.conn)
        return self.conn.root

    def __exit__(self, type, value, traceback):
        if self.bg_thread_enabled:
            self.bg_thread.stop()
        self.conn.close()

    def prompt(self, remote_prompt_method):
        # interactive prompts need to read standard input
        # and manage the rpyc connection at the same time.
        # it could be possible to manage this as an event
        # loop, but if we do, we cannot provide features
        # of a libreadline-enabled prompt.
        # that's why a background thread managing rpyc events
        # is required in this case.
        assert self.bg_thread_enabled
        prompt = remote_prompt_method(self)
        while True:
            try:
                line = raw_input()
            except:
                print '\nInterrupted.'
                break
            try:
                prompt.write(line + '\n')
                prompt.flush()
            except:
                print '\nRemote shell ended.'
                break

    def sql_prompt(self):
        self.prompt(self.conn.root.sql_prompt)

    # remotely callable methods
    def exposed_stop(self):
        os.kill(os.getpid(), signal.SIGINT)

    def exposed_write(self, s):
        sys.stdout.write(s)
        sys.stdout.flush()

    def exposed_flush(self):
        sys.stdout.flush()

