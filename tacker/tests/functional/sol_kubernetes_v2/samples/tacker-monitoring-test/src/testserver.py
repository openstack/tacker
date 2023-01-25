# Copyright (C) 2022 Fujitsu
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import json
import os
import threading
import urllib
import urllib.request
import uuid

from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

PORT = 55555
PROM_RULE_DIR = '/etc/prometheus/rules'

server_notification_alarm_map = {}


_body_base = {
    'receiver': 'receiver',
    'status': 'firing',
    'alerts': [
    ],
    'groupLabels': {},
    'commonLabels': {
        'alertname': 'NodeInstanceDown',
        'job': 'node'
    },
    'commonAnnotations': {
        'description': 'sample'
    },
    'externalURL': 'http://controller147:9093',
    'version': '4',
    'groupKey': '{}:{}',
    'truncatedAlerts': 0
}


class PeriodicTask():
    def __init__(self):
        self.remote_url = os.getenv('TEST_REMOTE_URI')
        print(f"url: {str(self.remote_url)}")
        self.schedule_next()
        self.stored_alerts_fm = {}

    def schedule_next(self):
        self.timer = threading.Timer(10, self.run)
        self.timer.start()

    def server_notification_task(self):
        print("server_notification_task: num of items: %s" %
              str(len(server_notification_alarm_map.keys())))
        for v in server_notification_alarm_map.values():
            try:
                if ('fault_action' in v and 'fault_id' in v):
                    url = v['fault_action']
                    body = {
                        'notification': {
                            'alarm_id': v['alarm_id'],
                            'fault_id': v['fault_id'],
                            'fault_type': '10'
                        }
                    }
                    headers = {
                        'Content-Type': 'application/json',
                    }

                    req = urllib.request.Request(
                        url, json.dumps(body).encode('utf-8'), headers)
                    with urllib.request.urlopen(req) as res:
                        print(f"res status: {str(res.status)}")
            except Exception as ex:
                print(str(ex))

    def _prometheus_plugin_task(self, grp, filename):
        alerts_pm = []
        alerts_fm = []
        alerts_auto_scale = []
        use_stored_alerts = False

        if filename in self.stored_alerts_fm:
            print("use_stored_alerts")
            stored_alerts = self.stored_alerts_fm[filename]
            for a in stored_alerts:
                a['status'] = 'resolved'
            del self.stored_alerts_fm[filename]
            alerts_fm = stored_alerts
            use_stored_alerts = True

        for rule in grp['rules']:
            if 'labels' not in rule or 'function_type' not in rule['labels']:
                continue
            alt = {
                'status': 'firing',
                'labels': rule['labels'],
                'annotations': {'value': 99},
                'startsAt': datetime.now().isoformat(),
                'fingerprint': str(uuid.uuid4())
            }
            if rule['labels']['function_type'] == 'vnfpm':
                alt['annotations'] = {'value': 99}
                alerts_pm.append(alt)
            if (not use_stored_alerts and
               rule['labels']['function_type'] == 'vnffm'):
                alt['annotations'] = {
                    'fault_type': 'fault_type',
                    'probable_cause': 'probable_cause'}
                alerts_fm.append(alt)
            if rule['labels']['function_type'] == 'auto_scale':
                alt['annotations'] = {}
                alerts_auto_scale.append(alt)

        if not use_stored_alerts and len(alerts_fm) > 0:
            self.stored_alerts_fm[filename] = alerts_fm

        return (alerts_pm, alerts_fm, alerts_auto_scale)

    def prometheus_plugin_task(self):
        print(f"prometheus_plugin_task: {PROM_RULE_DIR}")
        for entry in os.scandir(path=PROM_RULE_DIR):
            if not entry.is_file():
                continue
            print(f"file: {entry.name}")
            try:
                with open(PROM_RULE_DIR + '/' + entry.name) as f:
                    rules = json.load(f)
                    if 'groups' not in rules:
                        continue
                    for grp in rules['groups']:
                        if 'rules' not in grp:
                            continue
                        pm, fm, scale = self._prometheus_plugin_task(
                            grp, entry.name)
                        for x in [(pm, '/pm_event'), (fm, '/alert'),
                                  (scale, '/alert/vnf_instances')]:
                            if len(x[0]) == 0:
                                continue
                            body = copy.deepcopy(_body_base)
                            body['alerts'] = x[0]
                            headers = {'Content-Type': 'application/json'}
                            url = self.remote_url + x[1]
                            req = urllib.request.Request(
                                url, json.dumps(body).encode('utf-8'),
                                headers, method='POST')
                            print(f"uri: {str(url)}")
                            print(f"body: {str(body)}")
                            with urllib.request.urlopen(req) as res:
                                print(f"res status: {str(res.status)}")

            except Exception as ex:
                print(str(ex))

    def run(self):
        print("PeriodicTask run()")
        self.server_notification_task()
        self.prometheus_plugin_task()
        self.schedule_next()


class TestHttpServer(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def send_response(self, response_code, response_body):
        super().send_response(response_code)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self):
        print(f"GET {self.path}")
        response_body = '{"result": "ok"}\n'.encode('utf-8')
        self.send_response(HTTPStatus.NO_CONTENT, response_body)

    def do_DELETE_server_notification(self, alarm_id):
        if alarm_id in server_notification_alarm_map:
            del server_notification_alarm_map[alarm_id]
        self.send_response(HTTPStatus.NO_CONTENT, b'')

    def do_DELETE(self):
        print(f"DELETE {self.path}")
        parsed = urllib.parse.urlparse(self.path)
        path_detail = parsed.path.split('/')
        if (len(path_detail) == 7 and
                path_detail[1] == 'v2' and
                path_detail[3] == 'servers' and
                path_detail[5] == 'alarms'):
            self.do_DELETE_server_notification(path_detail[6])
        else:
            self.send_response(HTTPStatus.NO_CONTENT, b'')

    def do_POST_server_notification(self, decoded_data, tenant_id, server_id):
        print("POST_server_notification")
        try:
            print(json.dumps(json.loads(decoded_data),
                indent=2, ensure_ascii=False))
            print(str(uuid.uuid4()))

            _id = str(uuid.uuid4())
            data = json.loads(decoded_data)
            data['alarm_id'] = _id
            server_notification_alarm_map[_id] = data

            response_data = json.dumps(data) + '\n'
            response = HTTPStatus.CREATED, response_data.encode('utf-8')
        except Exception:
            response = (
                HTTPStatus.BAD_REQUEST, '{"result": "ng"}\n'.encode('utf-8'))

        self.send_response(response[0], response[1])

    def do_POST(self):
        content_length = int(self.headers.get('content-length'))
        raw_data = self.rfile.read(content_length)
        decoded_data = raw_data.decode('utf-8')
        print(f"POST {self.path}")
        parsed = urllib.parse.urlparse(self.path)
        path_detail = parsed.path.split('/')
        if (len(path_detail) == 6 and
                path_detail[1] == 'v2' and
                path_detail[3] == 'servers' and
                path_detail[5] == 'alarms'):
            self.do_POST_server_notification(
                decoded_data, path_detail[2], path_detail[4])
        else:
            try:
                print(json.dumps(json.loads(decoded_data),
                    indent=2, ensure_ascii=False))
                response = (HTTPStatus.NO_CONTENT,
                            '{"result": "ok"}\n'.encode('utf-8'))
            except Exception:
                response = (HTTPStatus.BAD_REQUEST,
                            '{"result": "ng"}\n'.encode('utf-8'))
            self.send_response(response[0], response[1])


periodic_task = PeriodicTask()
server = HTTPServer(('0.0.0.0', PORT), TestHttpServer)
server.serve_forever()
