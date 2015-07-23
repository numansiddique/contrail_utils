import argparse
import subprocess
import json
import sys


class ContrailRouteHelper(object):

    def __init__(self, args_str=None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        self.base_curl_cmd = ('curl -u %s:%s ' % (self._args.username,
                                                  self._args.password))

    def _parse_args(self, args_str):
        parser = argparse.ArgumentParser(description='OpenContrail Routing'
                                         ' Instance Helper')

        parser.add_argument("-U", "--username", help="Username of the tenant")
        parser.add_argument("-P", "--password", help="Password for the user")
        parser.add_argument("-s", "--api-server",
                            default='127.0.0.1',
                            help="API server address")
        parser.add_argument("-p", "--api-port", type=int,
                            default=8082,
                            help="API server port")
        parser.add_argument("-t", "--tenant-id", required=False,
                            help="tenant id")

        subparsers = parser.add_subparsers()
        list_parser = subparsers.add_parser('list')
        list_parser.set_defaults(func=self.list_virtual_networks)

        show_parser = subparsers.add_parser('show')
        show_parser.add_argument('network_id',
                                 help='show virtual network details of '
                                 ' network id ')
        show_parser.set_defaults(func=self.show_virtual_network)
        self._args = parser.parse_args()

    def _execute_curl_cmd(self, cmd):
        args = cmd.split()
        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        json_response = json.loads(stdout)
        return json_response

    def _extract_routing_instances(self, vnet):
        ris = []
        for ri in vnet['routing_instances']:
            ri_cmd = ('%s -s %s' % (self.base_curl_cmd, ri['href']))
            route_instance = self._execute_curl_cmd(ri_cmd)['routing-instance']
            ri_info = {'fq_name': route_instance['fq_name'],
                       'uuid': route_instance['uuid'],
                       'route_targets': []}
            for rt in route_instance.get('route_target_refs', []):
                rt_cmd = ('%s -s %s' % (self.base_curl_cmd,
                                        rt['href']))
                route_target = self._execute_curl_cmd(rt_cmd)
                route_target = route_target['route-target']
                rt_info = {'fq_name': route_target['fq_name'],
                           'uuid': route_target['uuid'],
                           'target': route_target['name']}
                ri_info['route_targets'].append(rt_info)
            ris.append(ri_info)
        return ris

    def list_virtual_networks(self):
        vns_cmd = ('%s -s http://%s:%s/virtual-networks'
                   % (self.base_curl_cmd, self._args.api_server,
                      self._args.api_port))
        virtual_nets = self._execute_curl_cmd(vns_cmd)
        total_virtual_nets = []
        for vn in virtual_nets['virtual-networks']:
            # get details about the virtual-network
            vn_cmd = ('%s -s %s' % (self.base_curl_cmd, vn['href']))
            vnet = self._execute_curl_cmd(vn_cmd)['virtual-network']
            tenant_id = vnet['parent_uuid'].replace("-", "")
            if self._args.tenant_id and self._args.tenant_id != tenant_id:
                continue

            vnet_info = {'uuid': vnet['uuid'],
                         'fq_name': vnet['fq_name'],
                         'tenant_id': tenant_id}
            routing_instances = self._extract_routing_instances(vnet)
            vnet_info['routing_instances'] = routing_instances
            total_virtual_nets.append(vnet_info)

        self._print_virtual_networks(total_virtual_nets)

    def show_virtual_network(self):
        vn_cmd = ('%s -s http://%s:%s/virtual-network/%s'
                  % (self.base_curl_cmd, self._args.api_server,
                     self._args.api_port, self._args.network_id))
        vnet = self._execute_curl_cmd(vn_cmd)['virtual-network']
        tenant_id = vnet['parent_uuid'].replace("-", "")
        if self._args.tenant_id and self._args.tenant_id != tenant_id:
            return

        vnet_info = {'uuid': vnet['uuid'],
                     'fq_name': vnet['fq_name'],
                     'tenant_id': tenant_id}
        routing_instances = self._extract_routing_instances(vnet)
        vnet_info['routing_instances'] = routing_instances
        self._print_virtual_networks([vnet_info])

    def _print_virtual_networks(self, virtual_nets):
        print 'Virtual Network details'
        print '********************************'
        for vnet in virtual_nets:
            print 'Virtual Network uuid : ', vnet['uuid']
            print 'Virtual Network fq-name : ', vnet['fq_name']
            print 'Virtual Network tenant id : ', vnet['tenant_id']
            print 'Virtual Network Routing instances :'
            for ri in vnet['routing_instances']:
                print '\t Routing Instance uuid : ', ri['uuid']
                print '\t Routing Instance fq_name :', ri['fq_name']
                if ri['route_targets']:
                    print '\t Routing Instance - Route targets :'
                    for rt in ri['route_targets']:
                        print '\t\tRoute target fq_name :', rt['fq_name']
                        print '\t\tRoute target uuid :', rt['uuid']
                        print '\t\tRoute target target :', rt['target']
                        print '\t\t%%%%%%%%%%%%%%%%%%%%%%%%%'
                else:
                    print '\t No Route targets'

                print '\t#######################'
            print '**************************************\n'
        print '\nEND\n'


def main(args_str=None):
    route_helper = ContrailRouteHelper(args_str)
    route_helper._args.func()

if __name__ == '__main__':
    main()

