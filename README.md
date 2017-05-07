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
