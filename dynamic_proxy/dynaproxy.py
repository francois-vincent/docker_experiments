# encoding: utf-8

import os
import socket
import threading

from clingon import clingon

DEBUG = True

# TODO replace print() with true logging
# TODO manage backend connections the other way: with a pool of long standing connections


def timeout_runner(timeout, func, *args, **kwargs):
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.start()
    thread.join(timeout)
    return not thread.is_alive()


class HostsManager(object):
    hosts = []
    index = 0
    refresher = None
    mutex = threading.Lock()

    @classmethod
    def initialize(cls, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(cls, k, v)
        cls.start()

    @classmethod
    def start(cls):
        cls.get_service_hosts()
        cls.refresher = threading.Timer(cls.refresh, cls.start)
        cls.refresher.start()

    @classmethod
    def stop(cls):
        if cls.refresher:
            cls.refresher.cancel()

    @classmethod
    def dig_dns(cls):
        cls.output = os.popen('dig @{} {}'.format(cls.dns, cls.service)).read()

    @classmethod
    def dig_dns_timeout(cls):
        cls.output = None
        timeout_runner(cls.timeout, cls.dig_dns)
        if cls.output is None:
            print("Warning: no DNS ({}) service found".format(cls.dns))
            return []
        else:
            return cls.output.split('\n')

    @classmethod
    def get_service_hosts(cls):
        hosts = [x.split()[4] for x in cls.dig_dns_timeout() if x.startswith(cls.service)]
        cls.mutex.acquire()
        cls.hosts = hosts
        cls.mutex.release()
        if not hosts:
            print("Warning: no service ({}) found".format(cls.service))
        elif DEBUG:
            print("Found hosts: {}".format(hosts))

    @classmethod
    def get_next_host(cls):
        cls.mutex.acquire()
        retries = 2
        try:
            while retries:
                try:
                    host = cls.hosts[cls.index]
                    cls.index += 1
                    return host
                except IndexError:
                    cls.index = 0
                    retries -= 1
        finally:
            cls.mutex.release()


def dispatcher(back, front):
    back.settimeout(1)
    try:
        data = 1
        while data:
            data = back.recv(32)
            front.sendall(data)
    except:
        pass


@clingon.clize
def launcher(dns='172.17.42.1', service='whoami.dev.docker',
             front_port=8000, back_port=8000, refresh=4000, timeout=400):
    """
    This is a dynamic tcp reverse proxy designed to work with skydock / skydns.
    It is designed to work with generic tcp services (named tcp-services below).
    It dispatches incoming requests to tcp-service hosts in roundrobin.
    The skydns service is requested in 3 cases:
     - at start of dynaproxy,
     - every 'refresh' time, to find new tcp-service hosts,
     - on each timeout on a tcp-service request.
    This is a POC with a naive single thread blocking implementation.
    """
    refresh_s = refresh / 1000.0
    timeout_s = timeout / 1000.0
    HostsManager.initialize(dns=dns, service=service, timeout=timeout_s, refresh=refresh_s)
    front_host = ('0.0.0.0', front_port)
    if DEBUG:
        print("Load balancer started @{}".format(front_host))
    front = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    front.bind(front_host)
    front.listen(1)
    try:
        while True:
            connection, client_address = front.accept()
            try:
                if DEBUG:
                    print("  ---------\n  Connection from {}".format(client_address))
                back, retries = None, 3
                while retries:
                    retries -= 1
                    back_ip = HostsManager.get_next_host()
                    if not back_ip:
                        HostsManager.get_service_hosts()
                        continue
                    else:
                        back_host = (back_ip, back_port)
                        back = socket.create_connection(back_host, timeout_s)
                        if back:
                            if DEBUG:
                                print("  Connected to {}".format(back_host))
                            break
                        else:
                            if DEBUG:
                                print("  Can't connect to {}".format(back_host))
                            HostsManager.get_service_hosts()
                            continue
                if DEBUG and not back:
                    print("  No backend available")
                if back:
                    thread = threading.Thread(target=dispatcher, args=(connection, back))
                    thread.start()
                    dispatcher(back, connection)
                    if DEBUG:
                        print("  Data collected from {}".format(back_host))
            finally:
                if DEBUG:
                    print("  Close connection to {}".format(client_address))
                    if back:
                        print("  Close connection to {}".format(back_host))
                connection.close()
                if back:
                    back.close()
    except KeyboardInterrupt:
        print("Interrupted by Ctrl-C")
    finally:
        front.close()
        HostsManager.stop()
        if DEBUG:
            print("Load balancer closed")
            print("{} active thread(s) left".format(threading.active_count() - 1))
