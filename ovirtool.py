#!/usr/bin/python3

import ovirtsdk4 as sdk
import ovirtsdk4.types as types

from argparse import ArgumentParser
from getpass import getpass
from subprocess import Popen, PIPE

import keyring

def connect(url, user, pw, pem):
    conn = sdk.Connection(
        url=url,
        username=user,
        password=pw,
        ca_file=pem,
    )

    conn.authenticate()

    return conn

class OVirt:
    _conn = None

    def __init__(self, conn):
        self._conn = conn

    def _get_system_service(self):
        return self._conn.system_service()

    def _get_vms_service(self):
        system_service = self._get_system_service()
        return system_service.vms_service()

    def _get_vms(self):
        vms_service = self._get_vms_service()
        return vms_service.list()

    def list_vms(self):
        vms = self._get_vms()

        for vm in vms:
            #print(f'{vm.status:6s} {vm.creation_time:16s} {vm.start_time:16s} {vm.name:20s} {vm.display.type.name:8s} {vm.guest_operating_system.distribution or ""}')
            print(f'{vm.status:6s} {str(vm.creation_time):34s} {str(vm.start_time or ""):34s} {vm.name:20s} {vm.id} {vm.display.type.name:8s}')

    def _get_vm(self, name=None):
        vms_service = self._get_vms_service()
        vms = self._get_vms()

        vm = next(( v for v in vms if v.name == name ))
        vm_service = vms_service.vm_service(vm.id)

        return vm, vm_service

    def connect_vm(self, method="remote-viewer", name=None):
        vm, vm_service = self._get_vm(name=name)
        console_service = self._get_spice_console_service(vm_service)

        vv = console_service.remote_viewer_connection_file()

        if method == "remote-viewer":
            self._remote_viewer(vv)

    def _get_spice_console_service(self, vm_service):
        consoles_service = vm_service.graphics_consoles_service()
        consoles = consoles_service.list(current=True)
        console = next(( c for c in consoles if c.protocol == types.GraphicsType.SPICE ))
        return consoles_service.console_service(console.id)
        
    def _remote_viewer(self, vv):
        cmd = "remote-viewer -"
        #subprocess.run(cmd.split(" "), )
        with Popen(cmd.split(' '), stdin=PIPE) as p:
            p.communicate(vv.encode("utf8"))


parser = ArgumentParser()
parser.add_argument("--host", required=True)
parser.add_argument("--pem", required=True) # TODO: auto retrieve
parser.add_argument("-u", "--user", required=True)
parser.add_argument("-l", "--list-vms", action="store_true")
parser.add_argument("-c", "--connect")

args = parser.parse_args()

url=f'https://{args.host}/ovirt-engine/api'

conn = None

pw = keyring.get_password(url, args.user)

if not pw:
    pw = getpass(prompt="Password: ")
    conn = connect(url, args.user, pw, args.pem)

    save = input("Save password to keyring? (y/n): ")
    if save == 'y': 
        keyring.set_password(url, args.user, pw)
        print("Password saved to keyring.")
    else:
        print("Not saving password to keyring")
else:
    conn = connect(url, args.user, pw, args.pem)
    

ovirt = OVirt(conn)

if args.list_vms:
    ovirt.list_vms()
elif args.connect:
    ovirt.connect_vm(name=args.connect)
