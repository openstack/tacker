# Copyright 2012, VMware, Inc.
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


from unittest import mock

import oslo_i18n

from tacker.agent.linux import utils
from tacker.tests import base
from tacker.tests.common import helpers


_marker = object()


class AgentUtilsExecuteTest(base.BaseTestCase):
    def setUp(self):
        super(AgentUtilsExecuteTest, self).setUp()
        self.test_file = self.get_temp_file_path('test_execute.tmp')
        open(self.test_file, 'w').close()
        self.process = mock.patch('eventlet.green.subprocess.Popen').start()
        self.process.return_value.returncode = 0
        self.mock_popen = self.process.return_value.communicate

    def test_without_helper(self):
        expected = "%s\n" % self.test_file
        self.mock_popen.return_value = [expected, ""]
        result = utils.execute(["ls", self.test_file])
        self.assertEqual(result, expected)

    def test_with_helper(self):
        expected = "ls %s\n" % self.test_file
        self.mock_popen.return_value = [expected, ""]
        result = utils.execute(["ls", self.test_file], root_helper='echo')
        self.assertEqual(result, expected)

    def test_stderr_true(self):
        expected = "%s\n" % self.test_file
        self.mock_popen.return_value = [expected, ""]
        out = utils.execute(["ls", self.test_file], return_stderr=True)
        self.assertIsInstance(out, tuple)
        self.assertEqual(out, (expected, ""))

    def test_check_exit_code(self):
        self.mock_popen.return_value = ["", ""]
        stdout = utils.execute(["ls", self.test_file[:-1]],
                               check_exit_code=False)
        self.assertEqual("", stdout)

    def test_execute_raises(self):
        self.mock_popen.side_effect = RuntimeError
        self.assertRaises(RuntimeError, utils.execute,
                          ["ls", self.test_file[:-1]])

    def test_process_input(self):
        expected = "%s\n" % self.test_file[:-1]
        self.mock_popen.return_value = [expected, ""]
        result = utils.execute(["cat"], process_input="%s\n" %
                               self.test_file[:-1])
        self.assertEqual(result, expected)

    def test_with_addl_env(self):
        expected = "%s\n" % self.test_file
        self.mock_popen.return_value = [expected, ""]
        result = utils.execute(["ls", self.test_file],
                               addl_env={'foo': 'bar'})
        self.assertEqual(result, expected)

    def test_return_code_log_error_raise_runtime(self):
        self.mock_popen.return_value = ('', '')
        self.process.return_value.returncode = 1
        with mock.patch.object(utils, 'LOG') as log:
            self.assertRaises(RuntimeError, utils.execute,
                              ['ls'])
            self.assertTrue(log.error.called)

    def test_return_code_log_error_no_raise_runtime(self):
        self.mock_popen.return_value = ('', '')
        self.process.return_value.returncode = 1
        with mock.patch.object(utils, 'LOG') as log:
            utils.execute(['ls'], check_exit_code=False)
            self.assertTrue(log.error.called)

    def test_return_code_log_debug(self):
        self.mock_popen.return_value = ('', '')
        with mock.patch.object(utils, 'LOG') as log:
            utils.execute(['ls'])
            self.assertTrue(log.debug.called)

    def test_return_code_log_error_change_locale(self):
        ja_output = 'std_out in Japanese'
        ja_error = 'std_err in Japanese'
        ja_message_out = oslo_i18n._message.Message(ja_output)
        ja_message_err = oslo_i18n._message.Message(ja_error)
        ja_translate_out = oslo_i18n._translate.translate(ja_message_out, 'ja')
        ja_translate_err = oslo_i18n._translate.translate(ja_message_err, 'ja')
        self.mock_popen.return_value = (ja_translate_out, ja_translate_err)
        self.process.return_value.returncode = 1

        with mock.patch.object(utils, 'LOG') as log:
            utils.execute(['ls'], check_exit_code=False)
            self.assertIn(ja_translate_out, str(log.error.call_args_list))
            self.assertIn(ja_translate_err, str(log.error.call_args_list))

    def test_return_code_raise_runtime_log_fail_as_error(self):
        self.mock_popen.return_value = ('', '')
        self.process.return_value.returncode = 1
        with mock.patch.object(utils, 'LOG') as log:
            self.assertRaises(RuntimeError, utils.execute,
                              ['ls'])
            self.assertTrue(log.error.called)

    def test_encode_process_input(self):
        bytes_idata = helpers.compact_byte("%s\n" % self.test_file[:-1])
        bytes_odata = helpers.compact_byte("%s\n" % self.test_file)
        self.mock_popen.return_value = [bytes_odata, b'']
        result = utils.execute(['cat'], process_input=bytes_idata)
        self.mock_popen.assert_called_once_with(bytes_idata)
        self.assertEqual(bytes_odata, result)

    def test_return_str_data(self):
        str_data = "%s\n" % self.test_file
        self.mock_popen.return_value = [str_data, '']
        result = utils.execute(['ls', self.test_file], return_stderr=True)
        self.assertEqual((str_data, ''), result)


class AgentUtilsExecuteEncodeTest(base.BaseTestCase):
    def setUp(self):
        super(AgentUtilsExecuteEncodeTest, self).setUp()
        self.test_file = self.get_temp_file_path('test_execute.tmp')
        open(self.test_file, 'w').close()

    def test_decode_return_data(self):
        str_data = helpers.compact_byte("%s\n" % self.test_file)
        result = utils.execute(['ls', self.test_file], return_stderr=True)
        self.assertEqual((str_data, helpers.compact_byte('')), result)
