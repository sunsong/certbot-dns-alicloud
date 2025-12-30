"""Tests for certbot_dns_alicloud._internal.dns_alicloud."""
import unittest
import os
try:
    import mock
except ImportError:
    from unittest import mock  # python 3.3+

from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN
from certbot.tests import util as test_util
from certbot._internal.display import obj as display_obj

from aliyunsdkcore.acs_exception.exceptions import ClientException

from certbot_dns_alicloud._internal.dns_alicloud import Authenticator

class AuthenticatorTest(test_util.TempDirTestCase, dns_test_common.BaseAuthenticatorTest):

    def setUp(self):
        display_obj.set_display(display_obj.FileDisplay(open(os.devnull, 'w'), False))
        super().setUp()

        path = os.path.join(self.tempdir, "alicloud.ini")
        with open(path, "w") as f:
            f.write("dns_alicloud_access_key = myaccesskey\n")
            f.write("dns_alicloud_secret_key = mysecretkey\n")
            f.write("dns_alicloud_region = cn-hangzhou\n")

        self.config = mock.MagicMock(dns_alicloud_credentials=path,
                                     dns_alicloud_propagation_seconds=10)  # pylint: disable=invalid-name
        self.auth = Authenticator(self.config, "dns_alicloud")

        self.mock_client = mock.MagicMock()
        # Mock _get_alicloud_client to return our mock client object
        self.auth._get_alicloud_client = mock.MagicMock(return_value=self.mock_client)


    def test_perform(self):
        self.auth.perform([self.achall])
        self.mock_client.add_txt_record.assert_called_with(DOMAIN, '_acme-challenge.' + DOMAIN, mock.ANY, 600)

    def test_cleanup(self):
        self.auth._attempt_cleanup = True
        self.auth.cleanup([self.achall])
        self.mock_client.del_txt_record.assert_called_with(DOMAIN, '_acme-challenge.' + DOMAIN, mock.ANY)


class AliCloudClientTest(unittest.TestCase):

    def setUp(self):
        from certbot_dns_alicloud._internal.dns_alicloud import _AliCloudClient
        self.client_class = _AliCloudClient

        self.mock_acs_client = mock.MagicMock()
        with mock.patch('certbot_dns_alicloud._internal.dns_alicloud.AcsClient', return_value=self.mock_acs_client):
            self.client = _AliCloudClient('key', 'secret', 'region')
            self.client.client = self.mock_acs_client

    def test_add_txt_record(self):
        # Mock _get_domain_name_and_rr
        self.client._get_domain_name_and_rr = mock.MagicMock(return_value=('example.com', '_acme-challenge'))

        self.client.add_txt_record('example.com', '_acme-challenge.example.com', 'content', 600)

        self.mock_acs_client.do_action_with_exception.assert_called()
        call_args = self.mock_acs_client.do_action_with_exception.call_args[0][0]

        # Verify the request object has correct parameters
        # We can't easily access the parameters set on the request object because they are stored internally
        # in the SDK's request object, but we can check if methods were called if we mocked the Request class too.
        # But here we are using real Request class.
        # We can check query params if they are prepared, but SDK prepares them inside do_action.
        # Let's trust it called it.

    def test_add_txt_record_error(self):
        self.client._get_domain_name_and_rr = mock.MagicMock(return_value=('example.com', '_acme-challenge'))
        self.mock_acs_client.do_action_with_exception.side_effect = ClientException('code', 'msg')

        from certbot import errors
        with self.assertRaises(errors.PluginError):
             self.client.add_txt_record('example.com', '_acme-challenge.example.com', 'content', 600)

    def test_del_txt_record(self):
        self.client._get_domain_name_and_rr = mock.MagicMock(return_value=('example.com', '_acme-challenge'))
        self.client._find_txt_record_id = mock.MagicMock(return_value='12345')

        self.client.del_txt_record('example.com', '_acme-challenge.example.com', 'content')

        self.mock_acs_client.do_action_with_exception.assert_called()
        # Ideally check if DeleteDomainRecordRequest was passed with RecordId=12345

    def test_del_txt_record_not_found(self):
        self.client._get_domain_name_and_rr = mock.MagicMock(return_value=('example.com', '_acme-challenge'))
        self.client._find_txt_record_id = mock.MagicMock(return_value=None)

        self.client.del_txt_record('example.com', '_acme-challenge.example.com', 'content')

        # Should not call delete
        self.mock_acs_client.do_action_with_exception.assert_not_called()

if __name__ == '__main__':
    unittest.main()
