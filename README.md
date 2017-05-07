# storserv

This is a demo key/value store that uses s3 as a backend, along with flask/wsgi and jwt tokens for the front end and can be deployed via elastic beanstalk.

## setup

In order for this to be deployed via elastic beanstalk, you'll need to configure a few things.

- Create a role for the beanstalk ec2 instances to access s3 and ssm param store
- Create an ssl cert in Certificate Manager
- Create an encryption key in KMS
- Create a parameter in ec2 parameter store called `storserv-jwt` and encrypt it with the key you just made in KMS
- Modify the 'PREFIX' config to set the bucket prefix
- Create an s3 bucket called '{PREFIX}-users'
- Create a key in the users bucket named after the user with a value that represents a bcrypted password
- Create a bucket for the user called '{PREFIX}-{username}'

## demo

The demo is available via curl at https://kvstore.phase2.net, with the username 'demo', password 'demo'

Quick reference:

    - /v1/ping (GET)
    - /v1/login (POST, username, password)
    - /v1/data/ (keystore)

## login

Once you've logged in, you'll receive a JWT token.  This token needs to be passed back to each subsequent API call via the header:

```
Authorization: Bearer <token>
```

## example

Request:
```
curl -k https://kvstore.phase2.net/v1/login -X POST -d username=demo -d password=demo
```

Response:
```
{
  "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJidWsiOiJzdG9yc2Vydi1kZW1vIiwiZXhwIjoxNDk0MTgxMDUzLjE1NjAxM30.Ow4IdDucwA1dEwo0SGpgWn58r9_rhhoJPDlSkH7CRT4"
}
```

Request:
```
curl -k -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJidWsiOiJzdG9yc2Vydi1kZW1vIiwiZXhwIjoxNDk0MTgxMDUzLjE1NjAxM30.Ow4IdDucwA1dEwo0SGpgWn58r9_rhhoJPDlSkH7CRT4' https://kvstore.phase2.net/v1/data/foo -X POST -d value=bar
```

Response:
```
{
  "key": "foo",
  "value": "bar"
}
```
