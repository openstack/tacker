# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import json
from wsgiref.simple_server import make_server


PORT = 6789


def handle_notification(environ, start_response):
    method = environ['REQUEST_METHOD']
    print("notification %s" % method)
    if method not in ['GET', 'POST']:
        print("  not support method")
        start_response('405 not suportted method',
                       [('Content-Type', 'application/problem+json')])
        problem_detail = {'status': 405,
                          'detail': "not supported method"}
        body = json.dumps(problem_detail)
        return [body.encode('utf-8')]

    authorization = environ.get("HTTP_AUTHORIZATION", "")
    version = environ.get("HTTP_VERSION", "")
    print("  authorizarion: %s" % authorization)
    print("  version: %s" % version)

    if method == 'POST':
        length = environ.get('CONTENT_LENGTH')
        print("  content_length: %s" % length)
        body = environ.get('wsgi.input').read(int(length))
        body = json.loads(body.decode('utf-8'))
        print("  request body: %s" % body)

    start_response('204 No content', [])
    return []


def handle_token(environ, start_response):
    method = environ['REQUEST_METHOD']
    print("token %s" % method)
    if method not in ['POST']:
        print("  not support method")
        start_response('405 not suportted method',
                       [('Content-Type', 'application/problem+json')])
        problem_detail = {'status': 405,
                          'detail': "not supported method"}
        body = json.dumps(problem_detail)
        return [body.encode('utf-8')]

    authorization = environ.get("HTTP_AUTHORIZATION", "")
    version = environ.get("HTTP_VERSION", "")
    content_type = environ.get("CONTENT_TYPE")
    print("  authorizarion: %s" % authorization)
    print("  version: %s" % version)
    print("  content_type: %s" % content_type)

    length = environ.get('CONTENT_LENGTH')
    print("  content_length: %s" % length)
    body = environ.get('wsgi.input').read(int(length))
    body = body.decode('utf-8')
    print("  request body: %s" % body)

    item = body.split('=')
    if (len(item) != 2 or
            item[0] != 'grant_type' or
            item[1] != 'client_credentials'):
        start_response('400 Bad Request', [])
        return []

    start_response('200 OK', [('Content-Type', 'application/json')])
    data = {
        "access_token": "2YotnFZFEjr1zCsicMWpAA",
        "token_type": "example",
        "expires_in": 3600,
        "example_parameter": "example_value"
    }
    body = json.dumps(data)
    return [body.encode('utf-8')]


def notif_endpoint_app(environ, start_response):
    path = environ['PATH_INFO']

    if path == "/notification":
        return handle_notification(environ, start_response)

    if path == "/token":
        return handle_token(environ, start_response)


if __name__ == '__main__':
    try:
        with make_server('', PORT, notif_endpoint_app) as httpd:
            httpd.serve_forever()
            httpd.handle_request()
    except KeyboardInterrupt:
        print()
        print("End.")
