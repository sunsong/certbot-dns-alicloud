certbot-dns-alicloud
====================

AliCloud DNS Authenticator plugin for Certbot

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, TXT records using the AliCloud DNS API.

Installation
------------

.. code-block:: bash

   pip install certbot-dns-alicloud

Usage
-----

As a third-party plugin, you must specify the authenticator using ``-a dns-alicloud``
or ``--authenticator dns-alicloud``. Unlike built-in certbot DNS plugins, the shorthand
``--dns-alicloud`` flag is not available.

Named Arguments
---------------

``-a dns-alicloud``
  Use the AliCloud DNS authenticator plugin. (Required)

``--dns-alicloud-credentials``
  AliCloud credentials INI file. (Required)

``--dns-alicloud-propagation-seconds``
  The number of seconds to wait for DNS to propagate before asking the ACME
  server to verify the DNS record. (Default: 10)

Credentials
-----------

Use of this plugin requires a configuration file containing AliCloud API
credentials, obtained from your AliCloud RAM Console.

.. code-block:: ini
   :name: alicloud.ini
   :caption: Example credentials file:

   dns_alicloud_access_key = your_access_key_id
   dns_alicloud_secret_key = your_access_key_secret
   dns_alicloud_region = cn-hangzhou

The path to this file can be provided interactively or using the
``--dns-alicloud-credentials`` command-line argument. Certbot records the path
to this file for use during renewal, but does not store the file's contents.

**Caution:** You should protect these API credentials as you would the password
to your AliCloud account. Users who can read this file can use these
credentials to issue arbitrary API calls on your behalf. Users who can cause
Certbot to run using these credentials can complete a ``dns-01`` challenge to
acquire new certificates or revoke existing certificates for associated
domains, even if those domains aren't being managed by this server.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).

Examples
--------

.. code-block:: bash
   :caption: To acquire a certificate for example.com

   certbot certonly \
     -a dns-alicloud \
     --dns-alicloud-credentials ~/.secrets/certbot/alicloud.ini \
     -d example.com

.. code-block:: bash
   :caption: To acquire a certificate for example.com, waiting 60 seconds for DNS propagation

   certbot certonly \
     -a dns-alicloud \
     --dns-alicloud-credentials ~/.secrets/certbot/alicloud.ini \
     --dns-alicloud-propagation-seconds 60 \
     -d example.com

.. code-block:: bash
   :caption: To acquire a wildcard certificate for *.example.com

   certbot certonly \
     -a dns-alicloud \
     --dns-alicloud-credentials ~/.secrets/certbot/alicloud.ini \
     -d "*.example.com"

Troubleshooting
---------------

**Error: "ambiguous option: --dns-alicloud could match --dns-alicloud-propagation-seconds, --dns-alicloud-credentials"**

This error occurs when trying to use ``--dns-alicloud`` as a shorthand. As a third-party
plugin, you must use ``-a dns-alicloud`` or ``--authenticator dns-alicloud`` to specify
the authenticator instead.

Incorrect:

.. code-block:: bash

   certbot certonly --dns-alicloud ...

Correct:

.. code-block:: bash

   certbot certonly -a dns-alicloud ...
