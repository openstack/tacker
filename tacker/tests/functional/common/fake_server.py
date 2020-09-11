#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
from datetime import datetime as dt
import http.server
import inspect
import json
import os
import threading

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class SingletonMixin:
    """Mixin class to make your class a Singleton class."""

    _instance = None
    _rlock = threading.RLock()
    _inside_instance = False

    @classmethod
    def get_instance(cls, *args, **kwargs):
        """Get *the* instance of the class, constructed when needed using(kw)args.

        Return the instance of the class. If it did not yet exist, create
        it by calling the "constructor" with whatever arguments and keyword
        arguments provided.

        This routine is thread-safe. It uses the *double-checked locking*
        design pattern ``https://en.wikipedia.org/wiki/Double-checked_locking``
        for this.

        :param args: Used for constructing the instance, when not performed
        yet.
        :param kwargs: Used for constructing the instance, when not
        perfored yet.
        :return: An instance of the class.
        """
        if cls._instance is not None:
            return cls._instance
        with cls._rlock:
            # re-check, perhaps it was created in the mean time...
            if cls._instance is None:
                cls._inside_instance = True
                try:
                    cls._instance = cls(*args, **kwargs)
                finally:
                    cls._inside_instance = False
        return cls._instance

    def __new__(cls, *args, **kwargs):
        """Raise Exception when not called from the :func:``instance``

        Class method.
        This method raises RuntimeError when not called from the
        instance class method.

        :param args: Arguments eventually passed to
        :func:``__init__``_.
        :param kwargs: Keyword arguments eventually passed to
        :func:``__init__``_
        :return: the created instance.
        """
        if cls is SingletonMixin:
            raise TypeError(
                "Attempt to instantiate\
                    mixin class {}".format(cls.__qualname__)
            )

        if cls._instance is None:
            with cls._rlock:
                if cls._instance is None and cls._inside_instance:
                    return super().__new__(cls, *args, **kwargs)

        raise RuntimeError(
            "Attempt to create a {}\
                instance outside of instance()".format(cls.__qualname__)
        )


class DummyRequestHander(http.server.CGIHTTPRequestHandler):
    """HTTP request handler for dummy server."""

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        return

    def _is_match_with_list(self):
        """Return given path is listed in dictionary or not.

        Return:
            True/False
        """
        manager = FakeServerManager.get_instance()
        func_uri_list = manager._methods[self.command]
        for objChkUrl in func_uri_list:
            # Check which requested path is in our list.
            LOG.debug('path for check:%s' % objChkUrl)
            if(self.path.startswith(objChkUrl)):
                return True

        return False

    def _returned_callback(self, mock_info):
        """Send responses to client. Called in do_* methods.

        This method do not handle message when error is occured.

        Args:
            mock_info (tuple): callback informations from caller.
        """
        request_headers = dict(self.headers._headers)
        request_body = self._parse_request_body()
        response_body_str = b''

        (status_code, mock_headers, mock_body) = self._get_mock_info(
            mock_info, request_headers, request_body)
        self.send_response(status_code)

        # Check what I should return to client ?
        if mock_info.get('content') is not None:
            response_body_str = open(mock_info.get('content'), 'rb').read()
        elif len(mock_body) > 0:
            response_body_str = json.dumps(mock_body).encode('utf-8')
            mock_headers['Content-Length'] = str(len(response_body_str))

        # Send custom header if exist
        for key, val in mock_headers.items():
            self.send_header(key, val)
        self.end_headers()

        if len(response_body_str) > 0:
            self.wfile.write(response_body_str)

        FakeServerManager.get_instance().add_history(self.path, RequestHistory(
            status_code=status_code,
            request_headers=request_headers,
            request_body=request_body,
            response_headers=copy.deepcopy(mock_headers),
            response_body=copy.deepcopy(mock_body))
        )

    def _parse_request_body(self):
        if 'content-length' not in self.headers:
            return {}

        request_content_len = int(self.headers.get('content-length'))
        if request_content_len == 0:
            return {}

        decode_request_body = self.rfile.read(
            request_content_len).decode('utf-8')

        return json.loads(decode_request_body)

    def _get_mock_info(self, mock_info, request_headers, request_body):
        """Call mock(callback) and get responses

        This method is called from _returned_callback().

        Args:
            mock_info (tuple): callback informations from caller.
            request_headers (dict): Request headers
            request_body (dict):  Request Bodies

        Returns:
            (tuple): status_code, response headers, response bodies.
                     response body will be converted into JSON string
                     with json.dumps().
        """
        # Prepare response contents
        func = mock_info.get('callback')
        status_code = mock_info.get('status_code')
        mock_headers = mock_info.get('response_headers')
        mock_body = mock_info.get('response_body')

        # Call function if callable.
        if callable(func):
            mock_body = func(request_headers, request_body)

        return (status_code, mock_headers, mock_body)

    def do_DELETE(self):
        raise NotImplementedError

    def do_GET(self):
        """Process GET request"""
        LOG.debug(
            '[Start] %s.%s()' %
            (self.__class__.__name__,
             inspect.currentframe().f_code.co_name))

        # Check URI in request.
        if self._is_match_with_list():
            # Request is registered in our list.
            self._returned_callback(
                FakeServerManager.get_instance()._funcs_gets[self.path])
        else:
            # Unregistered URI is requested
            LOG.debug('GET Recv. Unknown URL: "%s"' % self.path)
            self.send_response(http.HTTPStatus.BAD_REQUEST)
            self.end_headers()

        LOG.debug('[ End ] %s.%s()' %
                  (self.__class__.__name__,
                      inspect.currentframe().f_code.co_name))

    def do_POST(self):
        """Process POST request"""
        LOG.debug(
            '[Start] %s.%s()' %
            (self.__class__.__name__,
             inspect.currentframe().f_code.co_name))

        # URI might have trailing uuid or not.
        if self._is_match_with_list():
            # Request is registered in our list.
            self._returned_callback(
                FakeServerManager.get_instance()._funcs_posts[self.path])
        else:
            # Unregistered URI is requested
            LOG.debug('POST Recv. Unknown URL: "%s"' % self.path)
            self.send_response(http.HTTPStatus.BAD_REQUEST)
            self.end_headers()

        LOG.debug(
            '[ End ] %s.%s()' %
            (self.__class__.__name__,
             inspect.currentframe().f_code.co_name))

    def do_PUT(self):
        raise NotImplementedError


class RequestHistory:
    """Storage class for storing requested data(Maybe POSTed datas)."""

    def __init__(
            self,
            status_code,
            request_headers=None,
            request_body=None,
            response_headers=None,
            response_body=None):
        self.timestamp = dt.now()
        self.status_code = status_code
        self.request_headers = request_headers
        self.request_body = request_body
        self.response_headers = response_headers
        self.response_body = response_body


class FakeServerManager(SingletonMixin):
    """Manager class to manage dummy server setting and control"""

    SERVER_PORT = 9990

    def __init__(self):
        # Initialize class-specific variables.

        # Storage for request header/body and response header/body
        # history (dict) is updated using RequestHistory class.
        self._history = {}

        # Initialize function list for each request method.
        # DELETE/PUT method is listed but not supported currently.
        self._funcs_deletes = {}
        self._funcs_gets = {}
        self._funcs_posts = {}
        self._funcs_puts = {}
        self._methods = {
            'DELETE': self._funcs_deletes,
            'GET': self._funcs_gets,
            'POST': self._funcs_posts,
            'PUT': self._funcs_puts}

    def set_callback(
            self,
            method,
            uri,
            status_code=None,
            response_headers=None,
            response_body=None,
            content=None,
            callback=None):
        """Set callback function and some stuff for specified URI.

        ALL additional parameter is set default to None, so you have to
        specify what your callback-function need. response_header and
        response_body will be passed to callback.

        Args:
            method (str): Reqested method
            uri (str): Requested URI
            status_code (http.HTTPStatus): HTTP status code and
                                           reason phrase.
            response_headers (dict): Addtional response header.
            response_body (dict): Response body. Must be Jason Bourne
            content (str): File path that you want client to download.
            callback (callable): Callback function. Must return serializable
                                 object json.dumps() can handle.
        """
        callbacks = self._methods[method]
        callbacks[uri] = {
            'status_code': status_code or http.HTTPStatus.OK,
            'response_headers': response_headers or {},
            'response_body': response_body or {},
            'content': content,
            'callback': callback,
        }
        self._methods[method].update(callbacks)

        # Check file existence for content
        if content is not None:
            if not os.path.isfile(content):
                raise FileNotFoundError

        LOG.debug('Set callback for %s(%s): %s' %
                  (method, uri, callback))

    def add_history(self, path, history):
        """Add Request/Response header/body to history.

        This method maybe called in DummyRequestHandler._returned_callback()
        only. This method should not be called from outside of This class.

        Args:
            path (str): URI path
            history (RequestHistory): Storage container for each request.
        """
        with self._rlock:
            if path in self._history:
                self._history[path].append(history)
            else:
                self._history[path] = [history]

    def clear_history(self, path=None):
        """Clear Request/Response header/body of history.

        Args:
            path (str): URI path
        """
        with self._rlock:
            if not path:
                self._history = {}
                return

            if path in self._history:
                self._history.pop(path)

    def get_history(self, path=None):
        """Get Request/Response header/body from history.

        Args:
            path (str): URI path

        Returns:
            history list(RequestHistory): Storage container for each request.
        """
        history = copy.deepcopy(self._history)

        if not path:
            return history

        return history.get(path) or []

    def prepare_http_server(
            self,
            address="localhost",
            port=SERVER_PORT):
        """Set up HTTPd server your behalf.

        Args:
            address (str): bind address for listen
            port (int): por number for listen
        """
        LOG.debug(
            '[Start] %s.%s()' %
            (self.__class__.__name__,
             inspect.currentframe().f_code.co_name))
        self.objHttpd = http.server.HTTPServer(
            (address, port), DummyRequestHander)
        LOG.debug(
            '[ End ] %s.%s()' %
            (self.__class__.__name__,
             inspect.currentframe().f_code.co_name))

    def start_server(self):
        """Start server in thread."""
        LOG.debug('[START] %s()' % inspect.currentframe().f_code.co_name)
        threading.Thread(None, self.run).start()
        LOG.debug('[ END ] %s()' % inspect.currentframe().f_code.co_name)

    def run(self):
        """HTTPd server runner"""
        LOG.debug('[START] %s()' % inspect.currentframe().f_code.co_name)
        try:
            self.objHttpd.serve_forever()
        except KeyboardInterrupt:
            self.stop_server()
        LOG.debug('[ END ] %s()' % inspect.currentframe().f_code.co_name)

    def stop_server(self):
        """Stop HTTP Server"""
        LOG.debug('[START] %s()' % inspect.currentframe().f_code.co_name)
        self.objHttpd.shutdown()
        LOG.debug('[ END ] %s()' % inspect.currentframe().f_code.co_name)
