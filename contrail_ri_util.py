import argparse
import subprocess
import json
import sys
import uuid


class ContrailRouteHelper(object):

    def __init__(self, args_str=None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        if self._args.auth_token:
            self.base_curl_cmd = ('curl -H X-Auth-Token:%s'
                                  % (self._args.auth_token))
        else:
            if self._args.username is None or self._args.password is None:
                print ('Either username/password or auth token is required')
                sys.exit(1)

            self.base_curl_cmd = ('curl -u %s:%s ' % (self._args.username,
                                                      self._args.password))
        self.base_url = ('http://%s:%s' % (self._args.api_server,
                                           self._args.api_port))

    def _parse_args(self, args_str):
        parser = argparse.ArgumentParser(description='OpenContrail Routing'
                                         ' Instance Helper')

        parser.add_argument("-U", "--username", required=False,
                            help="Username of the tenant")
        parser.add_argument("-P", "--password", required=False,
                            help="Password for the user")
        parser.add_argument("-s", "--api-server",
                            default='127.0.0.1',
                            help="API server address")
        parser.add_argument("-a", "--auth-token",
                            required=False,
                            help="Auth token to be used instead of username/pwd")
        parser.add_argument("-p", "--api-port", type=int,
                            default=8082,
                            help="API server port")
        parser.add_argument("-t", "--tenant-id", required=False,
                            help="tenant id")

        subparsers = parser.add_subparsers()
        list_parser = subparsers.add_parser(
            'list', help='list all the virtual networks with '
            'routing instance information')
        list_parser.set_defaults(func=self.list_virtual_networks)

        show_parser = subparsers.add_parser('show')
        show_parser.add_argument('network_id',
                                 help='show virtual network details of '
                                 ' network id ')
        show_parser.set_defaults(func=self.show_virtual_network)

        enable_routing_parser = subparsers.add_parser(
            'enable-routing',
            help='allow routing between left and right network')
        enable_routing_parser.add_argument(
            '--left-network', help='network id of the left network',
            required=True)
        enable_routing_parser.add_argument(
            '--right-network', help='network id of the rigt network',
            required=True)
        enable_routing_parser.add_argument(
            '--routing-instance',
            required=False,
            help='Routing instance name')
        enable_routing_parser.add_argument(
            '--target',
            required=False,
            help='route target in the format <asn>:<target_number>')

        enable_routing_parser.set_defaults(func=self.enable_routing)

        disable_routing_parser = subparsers.add_parser(
            'disable-routing',
            help='disable routing between left and right network')
        disable_routing_parser.add_argument(
            '--left-network',
            help='network id or network fqname of the left network',
            required=True)
        disable_routing_parser.add_argument(
            '--right-network',
            help='network id of the rigt network',
            required=True)
        disable_routing_parser.add_argument(
            '--routing-instance',
            required=False,
            help='Routing instance name')
        disable_routing_parser.add_argument(
            '--target',
            required=True,
            help='route target in the format <asn>:<target_number>')

        disable_routing_parser.set_defaults(func=self.disable_routing)

        add_route_target = subparsers.add_parser(
            'add-route-target',
            help='Add a route target to the virtual network')
        add_route_target.add_argument(
            '--target',
            required=True,
            help='route target in the format <asn>:<target_number>')
        add_route_target.add_argument(
            '--routing-instance',
            required=False,
            help='Routing instance name')
        add_route_target.add_argument(
            '--network',
            help='network id or network fq_name of the virtual network')
        add_route_target.set_defaults(func=self.add_route_target)

        remove_route_target = subparsers.add_parser(
            'remove-route-target',
            help='Remove a route target of the virtual network')
        remove_route_target.add_argument(
            '--target',
            required=True,
            help='route target in the format <asn>:<target_number>')
        remove_route_target.add_argument(
            '--routing-instance',
            required=False,
            help='Routing instance name')
        remove_route_target.add_argument(
            '--network',
            help='network id or network fq_name of the virtual network')
        remove_route_target.set_defaults(func=self.remove_route_target)

        self._args = parser.parse_args()

    def _execute_curl_cmd(self, cmd, json_data=None, verbose=True):
        args = cmd.split()
        if json_data:
            json_data = json.JSONEncoder().encode(json_data)
            args.append(json_data)
        if verbose:
            print '\n'
            print ('Executing curl command ')
            if json_data:
                print ('%s%s' % (cmd, json_data))
            else:
                print cmd
            print '\n'

        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        try:
            json_response = json.loads(stdout)
        except:
            print 'Returned error response from server : ', stdout
            print stderr
            return None

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
        if self._args.tenant_id:
            try:
                parent_id = str(uuid.UUID(self._args.tenant_id))
                parent_id_str = '?parent_id=%s' % (parent_id)
                vns_cmd = ('%s%s' % (vns_cmd, parent_id_str))
            except:
                pass

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

    def _get_virtual_network(self, network, verbose=True):
        try:
            uuid.UUID(network)
            network_id = network
        except:
            network_id = self._get_id_from_fq_name([network],
                                                   'virtual-network')
            if not network_id:
                print ("Network %s not found " % (network))
                sys.exit(1)

        vn_cmd = ('%s -s http://%s:%s/virtual-network/%s'
                  % (self.base_curl_cmd, self._args.api_server,
                     self._args.api_port, network_id))
        vnet = self._execute_curl_cmd(vn_cmd, verbose=verbose)
        if not vnet:
            print ("Network %s not found " % (network))
            sys.exit(1)

        vnet = vnet['virtual-network']
        tenant_id = vnet['parent_uuid'].replace("-", "")
        if self._args.tenant_id and self._args.tenant_id != tenant_id:
            return

        vnet_info = {'uuid': vnet['uuid'],
                     'fq_name': vnet['fq_name'],
                     'tenant_id': tenant_id}
        routing_instances = self._extract_routing_instances(vnet)
        vnet_info['routing_instances'] = routing_instances
        return vnet_info

    def show_virtual_network(self):
        vnet_info = self._get_virtual_network(self._args.network_id)
        self._print_virtual_networks([vnet_info])

    def _print_virtual_networks(self, virtual_nets):
        print 'Virtual Network details'
        print '********************************'
        for vnet in virtual_nets:
            print 'Virtual Network uuid - ', vnet['uuid']
            print 'Virtual Network fq-name - ', vnet['fq_name']
            print 'Virtual Network tenant id - ', vnet['tenant_id']
            print 'Virtual Network Routing instances :'
            for ri in vnet['routing_instances']:
                print '\t Routing Instance uuid - ', ri['uuid']
                print '\t Routing Instance fq_name - ', ri['fq_name']
                if ri['route_targets']:
                    print '\t Routing Instance - Route targets :'
                    for rt in ri['route_targets']:
                        print '\t\tRoute target fq_name -', rt['fq_name']
                        print '\t\tRoute target uuid -', rt['uuid']
                        print '\t\tRoute target -', rt['target']
                        print '\t\t%%%%%%%%%%%%%%%%%%%%%%%%%'
                else:
                    print '\t No Route targets'

                print '\t#######################'
            print '**************************************\n'
        print '\nEND\n'

    def _get_id_from_fq_name(self, fq_name, res_type):
        json_data = {"fq_name": fq_name, "type": res_type}
        cmd = ('%s -X POST %s/fqname-to-id -H Content-Type:application/json'
               ' -d '
               % (self.base_curl_cmd, self.base_url))
        uuid = self._execute_curl_cmd(cmd, json_data=json_data)
        return uuid['uuid'] if uuid else None

    def _read_virtual_network(self, net_id=None, fq_name=None):
        if not id and fq_name:
            # get the id from fq_name
            net_id = self._get_id_from_fq_name(fq_name, 'virtual-network')
        vn_cmd = ('%s -s http://%s:%s/virtual-network/%s'
                  % (self.base_curl_cmd, self._args.api_server,
                     self._args.api_port, net_id))
        vnet = self._execute_curl_cmd(vn_cmd)['virtual-network']
        return vnet

    def _generate_rt_key(self, other_key):
        target_key = int(other_key[2]) + 10000
        return 'target:%s:%d' % (other_key[1], target_key)

    def _read_or_create_route_target(self, rt_key):
        rt_target = self._get_route_target(rt_key)
        if not rt_target:
            rt_target = self._create_route_target(rt_key)
        return rt_target

    def _create_route_target(self, rt_key):
        data = {"route-target": {"fq_name": rt_key}}
        cmd = ('%s -X POST %s/route-targets -H '
               'Content-Type:application/json -d '
               % (self.base_curl_cmd, self.base_url))
        rt_target = self._execute_curl_cmd(cmd, json_data=data)['route-target']
        return rt_target

    def _delete_route_target(self, rt_uuid=None, rt_key=None):
        if not rt_uuid and rt_key:
            rt_uuid = self._get_id_from_fq_name(rt_key, 'route-target')

        cmd = ('%s -X DELETE %s/route-target/%s'
               % (self.base_curl_cmd, self.base_url, rt_uuid))
        self._execute_curl_cmd(cmd)

    def _get_route_target(self, rt_key):
        rt_uuid = self._get_id_from_fq_name(rt_key, 'route-target')
        if not rt_uuid:
            return None

        cmd = ('%s -s %s/route-target/%s'
               % (self.base_curl_cmd, self.base_url, rt_uuid))
        try:
            rt = self._execute_curl_cmd(cmd)['route-target']
        except:
            return None
        return rt

    def _read_or_create_routing_instance(self, ri_fq_name):
        routing_instance = self._get_routing_instance(fq_name=ri_fq_name)
        if not routing_instance:
            routing_instance = self._create_routing_instance(ri_fq_name)
        return routing_instance

    def _get_routing_instance(self, ri_uuid=None, fq_name=None):
        if not ri_uuid and fq_name:
            ri_uuid = self._get_id_from_fq_name(fq_name, 'routing-instance')

        if not ri_uuid:
            return None

        cmd = ('%s -s %s/routing-instance/%s'
               % (self.base_curl_cmd, self.base_url, ri_uuid))
        try:
            ri = self._execute_curl_cmd(cmd)['routing-instance']
        except:
            return None
        return ri

    def _create_routing_instance(self, ri_fq_name):
        data = {"routing-instance": {"fq_name": ri_fq_name,
                                     "parent_type": "virtual-network",
                                     "uuid": None}}
        cmd = ('%s -X POST %s/routing-instances -H '
               'Content-Type:application/json -d '
               % (self.base_curl_cmd, self.base_url))
        rt_target = self._execute_curl_cmd(cmd, json_data=data)
        return rt_target['routing-instance']

    def _update_routing_instance(self, ri_uuid, rt_uuid, rt_fq_name, action):
        json_data = {"ref-type": "route-target",
                     "uuid": ri_uuid,
                     "ref-fq-name": rt_fq_name,
                     "ref-uuid": rt_uuid,
                     "operation": action,
                     "type": "routing-instance",
                     "attr": {"import_export": None}}

        cmd = ('%s -X POST %s/ref-update -H Content-Type:application/json '
               ' -d ' % (self.base_curl_cmd, self.base_url))
        self._execute_curl_cmd(cmd, json_data=json_data)

    def _delete_routing_instance(self, ri_uuid=None, ri_fq_name=None):
        if not ri_uuid and ri_fq_name:
            ri_uuid = self._get_id_from_fq_name(ri_fq_name, 'routing-instance')

        cmd = ('%s -X DELETE %s/routing-instance/%s'
               % (self.base_curl_cmd, self.base_url, ri_uuid))
        self._execute_curl_cmd(cmd)

    def _get_primary_routing_instance(self, vn):
        return vn['routing_instances'][0]

    def _get_routing_instance_for_vn(self, vn, ri_name):
        if not ri_name:
            return self._get_primary_routing_instance(vn)
        ri_fq_name = list(vn['fq_name'])
        ri_fq_name.append(ri_name)
        return self._get_routing_instance(fq_name=ri_fq_name)

    def _get_or_create_routing_instance_for_vn(self, vn, ri_name):
        if not ri_name:
            return self._get_primary_routing_instance(vn)

        ri_fq_name = list(vn['fq_name'])
        ri_fq_name.append(ri_name)
        return self._read_or_create_routing_instance(ri_fq_name)

    def enable_routing(self):
        left_net = self._get_virtual_network(self._args.left_network)
        right_net = self._get_virtual_network(self._args.right_network)

        if self._args.target:
            rt_key = ['target:%s' % (self._args.target)]
        else:
            existing_key = (
                left_net['routing_instances'][0]['route_targets'][0]['target'])
            existing_key = existing_key.split(':')
            rt_key = self._generate_rt_key(existing_key)

        # create a route target
        rt_target = self._read_or_create_route_target(rt_key)
        print 'Created route target : ', rt_target

        # associate the route target to the routing instances of the
        # virtual networks
        vn_list = [left_net, right_net]
        for vn in vn_list:
            ri = self._get_or_create_routing_instance_for_vn(
                vn, self._args.routing_instance)
            self._update_routing_instance(ri['uuid'], rt_target['uuid'],
                                          rt_target['fq_name'], 'ADD')

        left_net = self._get_virtual_network(self._args.left_network,
                                             verbose=False)
        right_net = self._get_virtual_network(self._args.right_network,
                                              verbose=False)
        self._print_virtual_networks([left_net, right_net])

    def _find_common_rt_target(self, vn_list):
        return None

    def disable_routing(self):
        left_net = self._get_virtual_network(self._args.left_network)
        right_net = self._get_virtual_network(self._args.right_network)

        if self._args.target:
            rt_key = ['target:%s' % (self._args.target)]
        else:
            # find the common target shared between left and right net
            rt_key = self._find_common_rt_target([left_net, right_net])
            if not rt_key:
                return

        rt_target = self._get_route_target(rt_key)
        if not rt_target:
            print ('Route target : %s not found. Exiting..'
                   % self._args.target)
            sys.exit()
        vn_list = [left_net, right_net]
        for vn in vn_list:
            ri = self._get_routing_instance_for_vn(vn,
                                                   self._args.routing_instance)
            if not ri:
                print ('Routing instance %s not found for virtual network [%s]'
                       % (self._args.routing_instance, str(vn['fq_name'])))
                continue

            self._update_routing_instance(ri['uuid'], rt_target['uuid'],
                                          rt_target['fq_name'], 'DELETE')

            if self._args.routing_instance:
                primary_ri = self._get_primary_routing_instance(vn)
                if primary_ri['uuid'] != ri['uuid']:
                    self._delete_routing_instance(ri_uuid=ri['uuid'])

        self._delete_route_target(rt_target['uuid'])

        left_net = self._get_virtual_network(self._args.left_network,
                                             verbose=False)
        right_net = self._get_virtual_network(self._args.right_network,
                                              verbose=False)
        self._print_virtual_networks([left_net, right_net])

    def _vn_route_target_update(self, action):
        vn = self._get_virtual_network(self._args.network)
        rt_key = ['target:%s' % (self._args.target)]
        rt_target = self._get_route_target(rt_key)
        if not rt_target:
            print ('Route target : %s not found. Exiting..'
                   % self._args.target)
            sys.exit()
        ri = self._get_primary_routing_instance(vn)
        self._update_routing_instance(ri['uuid'], rt_target['uuid'],
                                      rt_target['fq_name'], action)

        print ('%sED route target %s network [%s]'
               % (action, 'to' if action == 'ADD' else 'from',
                  self._args.network))
        print ('\n')
        vn = self._get_virtual_network(self._args.network)
        self._print_virtual_networks([vn])

    def add_route_target(self):
        self._vn_route_target_update('ADD')

    def remove_route_target(self):
        self._vn_route_target_update('DELETE')


def main(args_str=None):
    route_helper = ContrailRouteHelper(args_str)
    route_helper._args.func()

if __name__ == '__main__':
    main()
