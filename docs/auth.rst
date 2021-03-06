Authentication
==============

.. contents::
   :local:

Authentication with the Soledad server is made using `Twisted's Pluggable
Authentication system
<https://twisted.readthedocs.io/en/latest/core/howto/cred.html>`_. The
validation of credentials is performed by verifying a token provided by the
client.

There are currently two distinct authenticated entry points:

* A public TLS encrypted **Users API**, providing the *Synchronization* and
  *Blobs* services, verified against the Leap Platform
  ``tokens`` database.

* A local plaintext **Services API**, providing the delivery part of the
  *Incoming* service, authenticated against tokens defined in a file specified
  on the server configuration file.

Authorization header
--------------------

The client has to provide a token encoded in an HTTP auth header, as in::

    Authorization: Token <base64-encoded uuid:token>

If no token is provided, the request is considered an "anonymous" request.
Anonymous requests can only access `GET /`, which returns information about the
server (as the version of the server and runtime configuration options).

Special credentials for local services
--------------------------------------

Some special credentials can be added into a file
(``/etc/soledad/incoming.tokens``, by default) and then configured in the
Soledad Server configuration file. Currently, the only special credential
provided is for the `/incoming` API.

Implementation
--------------

Soledad Server package includes a systemd service file that spawns a ``twistd``
daemon that loads a `.tac file
<https://twistedmatrix.com/documents/12.2.0/core/howto/application.html#auto5>`_.
When the server is started, two services are spawned:

* A local entrypoint for services (serving on localhost only).
* A public entrypoint for users (serving on public IP).
* Localhost and public IP ports are configurable. Default is 2424 for public IP
  and 2525 for localhost.

.. code-block:: none

    .------------------------------------------------------.
    |                    soledad-server                    |
    |      (twisted.application.service.Application)       |
    '------------------------------------------------------'
       |                                                |
    .--------------.                      .----------------.
    | 0.0.0.0:2424 |                      | 127.0.0.1:2525 |
    |     (TLS)    |                      |     (TCP)      |
    '--------------'                      '----------------'
       |                                                |
    .----------------.             .----------------------.
    | Auth for users |             |  Auth for services   |
    |  (UsersRealm)  |             | (LocalServicesRealm) |
    '----------------'             '----------------------'
       |                                                |
    .------------------.        .-------------------------.
    |    Users API     |        |      Services API       |
    | (PublicResource) |        |     (LocalResource)     |
    '------------------'        '-------------------------'
       |  .-------.                .-----------------.  |
       '->| /sync |                |    /incoming    |<-'
       |  '-------'                | (delivery only) |
       |  .--------.               '-----------------'
       '->| /blobs |
          '--------'
