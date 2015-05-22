# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests setting the presto configure
"""
from mock import patch

from fabric.api import env
from prestoadmin import configure
from tests import utils


class TestConfigure(utils.BaseTestCase):
    def test_output_format_dict(self):
        conf = {'a': 'b', 'c': 'd'}
        self.assertEqual(configure.output_format(conf),
                         "a=b\nc=d")

    def test_output_format_list(self):
        self.assertEqual(configure.output_format(['a', 'b']),
                         'a\nb')

    def test_output_format_string(self):
        conf = "A string"
        self.assertEqual(configure.output_format(conf), conf)

    def test_output_format_int(self):
        conf = 1
        self.assertEqual(configure.output_format(conf), str(conf))

    @patch('prestoadmin.configure.configure_presto')
    @patch('prestoadmin.configure.util.get_coordinator_role')
    @patch('prestoadmin.configure.env')
    def test_worker_is_coordinator(self, env_mock, coord_mock, configure_mock):
        env_mock.host = "my.host"
        coord_mock.return_value = ["my.host"]
        configure.workers()
        assert not configure_mock.called

    @patch('prestoadmin.configure.w.get_conf')
    @patch('prestoadmin.configure.configure_presto')
    def test_worker_not_coordinator(self,  configure_mock, get_conf_mock):
        env.host = "my.host1"
        env.roledefs["worker"] = ["my.host1"]
        env.roledefs["coordinator"] = ["my.host2"]
        configure.workers()
        assert configure_mock.called

    @patch('prestoadmin.configure.configure_presto')
    @patch('prestoadmin.configure.coord.get_conf')
    def test_coordinator(self, coord_mock, configure_mock):
        env.roledefs['coordinator'] = ['master']
        env.host = 'master'
        coord_mock.return_value = {}
        configure.coordinator()
        assert configure_mock.called

    @patch('prestoadmin.configure.sudo')
    def test_deploy(self, sudo_mock):
        files = {"jvm.config": "a=b"}
        configure.deploy(files, "/my/remote/dir")
        sudo_mock.assert_any_call("mkdir -p /my/remote/dir")
        sudo_mock.assert_any_call("echo 'a=b' > /my/remote/dir/jvm.config")

    @patch('__builtin__.open')
    @patch('prestoadmin.configure.files.append')
    @patch('prestoadmin.configure.sudo')
    def test_deploy_node_properties(self, sudo_mock, append_mock, open_mock):
        file_manager = open_mock.return_value.__enter__.return_value
        file_manager.read.return_value = ("key=value")
        command = (
            "if ! ( grep -q 'node.id' /my/remote/dir/node.properties ); "
            "then "
            "uuid=$(uuidgen); "
            "echo node.id=$uuid >> /my/remote/dir/node.properties;"
            "fi; "
            "sed -i '/node.id/!d' /my/remote/dir/node.properties; ")
        configure.deploy_node_properties("key=value", "/my/remote/dir")
        sudo_mock.assert_called_with(command)
        append_mock.assert_called_with("/my/remote/dir/node.properties",
                                       "key=value", True)

    @patch('prestoadmin.configure.deploy')
    @patch('prestoadmin.configure.deploy_node_properties')
    def test_configure_presto(self, deploy_node_mock, deploy_mock):
        conf = {"node.properties": {"key": "value"}, "jvm.config": ["list"]}
        remote_dir = "/my/remote/dir"
        configure.configure_presto(conf, remote_dir)
        deploy_mock.assert_called_with({"jvm.config": "list"}, remote_dir)

    def test_escape_quotes_do_nothing(self):
        text = 'basic_text'
        self.assertEqual('basic_text', configure.escape_single_quotes(text))

    def test_escape_quotes_has_quote(self):
        text = "A quote! ' A quote!"
        self.assertEqual("A quote! '\\'' A quote!",
                         configure.escape_single_quotes(text))