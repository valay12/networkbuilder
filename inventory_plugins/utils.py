class Topology(request):
    LOCATION = {'Singapore': 'SNG',
                'London': 'LON',
                'New York': 'NYC'}
    def __init__(self, request):
        self.request = request
    def _get_neighbors(self, host_list):
        for i in range(len(host_list)):
            role = host_list[i]['role']
            downlinks = []
            uplinks = []
            peer = ''
            for neighbor in host_list:
            if host_list[i]['hostname'] == neighbor['hostname']:
                continue
            elif neighbor['role'][:-1] == 'DST':
                if role[:-1] == 'DST':
                peer = neighbor['hostname']
                else:
                uplinks.append(neighbor['hostname'])
            else:
                if role[:-1] == 'DST':
                downlinks.append(neighbor['hostname'])
            host_list[i]['uplinks'] = uplinks
            host_list[i]['downlinks'] = downlinks
            host_list[i]['peer'] = peer
        return host_list 