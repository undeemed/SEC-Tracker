# TLS Certificates

This folder is mounted into the nginx container at `/etc/nginx/ssl`.

Provide your TLS certs here:

- `fullchain.pem`
- `privkey.pem`

Do **not** commit private keys. `.gitignore` keeps this directory empty except for this README.

