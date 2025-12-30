"""DNS Authenticator for AliCloud."""
import json
import logging
from typing import Any
from typing import Callable
from typing import Optional

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkalidns.request.v20150109 import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109 import DeleteDomainRecordRequest
from aliyunsdkalidns.request.v20150109 import DescribeDomainRecordsRequest

from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

logger = logging.getLogger(__name__)

class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for AliCloud

    This Authenticator uses the AliCloud API to fulfill a dns-01 challenge.
    """

    description = ('Obtain certificates using a DNS TXT record (if you are using AliCloud for '
                   'DNS).')
    ttl = 600  # AliCloud DNS requires TTL to be between 600 and 86400 seconds

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.credentials: Optional[CredentialsConfiguration] = None

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None],
                             default_propagation_seconds: int = 10) -> None:
        super().add_parser_arguments(add, default_propagation_seconds)
        add('credentials', help='AliCloud credentials INI file.')

    def more_info(self) -> str:
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'the AliCloud API.'

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            'credentials',
            'AliCloud credentials INI file',
            {
                'access-key': 'AliCloud Access Key',
                'secret-key': 'AliCloud Secret Key',
                'region': 'AliCloud Region (optional, defaults to cn-hangzhou)',
            }
        )

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_alicloud_client().add_txt_record(domain, validation_name, validation, self.ttl)

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_alicloud_client().del_txt_record(domain, validation_name, validation)

    def _get_alicloud_client(self) -> "_AliCloudClient":
        if not self.credentials:  # pragma: no cover
            raise errors.Error("Plugin has not been prepared.")

        region = self.credentials.conf('region') or 'cn-hangzhou'
        return _AliCloudClient(
            self.credentials.conf('access-key'),
            self.credentials.conf('secret-key'),
            region
        )


class _AliCloudClient:
    """
    Encapsulates all communication with the AliCloud API.
    """

    def __init__(self, access_key: str, secret_key: str, region: str) -> None:
        self.client = AcsClient(access_key, secret_key, region)

    def add_txt_record(self, domain: str, record_name: str, record_content: str,
                       record_ttl: int) -> None:
        """
        Add a TXT record using the supplied information.

        :param str domain: The domain to use to look up the AliCloud zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        :param int record_ttl: The record TTL (number of seconds that the record may be cached).
        :raises certbot.errors.PluginError: if an error occurs communicating with the AliCloud API
        """

        # domain is unused but kept for interface compatibility
        del domain
        domain_name, rr = self._get_domain_name_and_rr(record_name)

        request = AddDomainRecordRequest.AddDomainRecordRequest()
        request.set_DomainName(domain_name)
        request.set_RR(rr)
        request.set_Type('TXT')
        request.set_Value(record_content)
        request.set_TTL(record_ttl)

        try:
            logger.debug('Attempting to add record to domain %s: %s', domain_name, rr)
            self.client.do_action_with_exception(request)
        except (ClientException, ServerException) as e:
            logger.error('Encountered AliCloud API Error adding TXT record: %s', e)
            raise errors.PluginError(f'Error communicating with the AliCloud API: {e}')

        logger.debug('Successfully added TXT record')

    def del_txt_record(self, domain: str, record_name: str, record_content: str) -> None:
        """
        Delete a TXT record using the supplied information.

        :param str domain: The domain to use to look up the AliCloud zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        """

        # domain is unused but kept for interface compatibility
        del domain
        try:
            domain_name, rr = self._get_domain_name_and_rr(record_name)
        except errors.PluginError as e:
            logger.debug('Encountered error finding domain_name during deletion: %s', e)
            return

        record_id = self._find_txt_record_id(domain_name, rr, record_content)

        if record_id:
            request = DeleteDomainRecordRequest.DeleteDomainRecordRequest()
            request.set_RecordId(record_id)

            try:
                self.client.do_action_with_exception(request)
                logger.debug('Successfully deleted TXT record.')
            except (ClientException, ServerException) as e:
                logger.warning('Encountered AliCloud API Error deleting TXT record: %s', e)
        else:
            logger.debug('TXT record not found; no cleanup needed.')

    def _get_domain_name_and_rr(self, record_name: str) -> tuple:
        """
        Split the record name into domain name and RR.

        :param str record_name: The record name (e.g. _acme-challenge.example.com)
        :returns: A tuple of (domain_name, rr)
        """
        domain_name_guesses = dns_common.base_domain_name_guesses(record_name)

        # We need to find which guess is the actual domain name in AliCloud
        # We can try to list records for each guess. If it succeeds, that's the domain.

        for domain_name in domain_name_guesses:
            request = DescribeDomainRecordsRequest.DescribeDomainRecordsRequest()
            request.set_DomainName(domain_name)
            request.set_PageSize(1)

            try:
                self.client.do_action_with_exception(request)
                # If we get here, the domain exists
                # Calculate RR
                # record_name = rr + "." + domain_name
                # rr = record_name - domain_name
                if record_name.endswith("." + domain_name):
                    rr = record_name[:-(len(domain_name) + 1)]
                elif record_name == domain_name:
                    rr = "@"
                else:
                    continue  # Should not happen if base_domain_name_guesses works as expected

                return domain_name, rr
            except (ClientException, ServerException):
                # If the domain doesn't exist or we don't have access, we'll get an error.
                # We continue to the next guess.
                pass

        raise errors.PluginError(f'Unable to determine AliCloud domain for {record_name}.')

    def _find_txt_record_id(self, domain_name: str, rr: str, record_content: str) -> Optional[str]:
        """
        Find the record_id for a TXT record with the given RR and content.
        """
        request = DescribeDomainRecordsRequest.DescribeDomainRecordsRequest()
        request.set_DomainName(domain_name)
        request.set_RRKeyWord(rr)
        request.set_TypeKeyWord('TXT')
        request.set_ValueKeyWord(record_content)

        try:
            response = self.client.do_action_with_exception(request)
            data = json.loads(response)
            records = data.get('DomainRecords', {}).get('Record', [])

            for record in records:
                if record.get('RR') == rr and record.get('Value') == record_content:
                    return record.get('RecordId')

        except (ClientException, ServerException) as e:
            logger.debug('Encountered AliCloud API Error getting TXT record_id: %s', e)

        return None
