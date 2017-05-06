import application as flaskr
import unittest
from mock import MagicMock, patch


class FlaskrTestCase(unittest.TestCase):

    def setUp(self):
        flaskr.application.config['TESTING'] = True
        flaskr.application.config['SECRET'] = 'foo'
        self.application = flaskr.application.test_client()

    def tearDown(self):
        pass

    def testPing(self):
        rv = self.application.get('/v1/ping')
        assert b'pong' in rv.data

    @patch('application.jwt.encode')
    @patch('application.bcrypt.checkpw')
    @patch('application.s3')
    def testLogin(self, ms3, mcheckpw, mencode):
        # Mock out s3 calls
        ms3.head_object = MagicMock()
        pwhash = MagicMock()
        ms3.get_object = MagicMock(return_value={'Body': pwhash})

        # Test a valid login
        pwhash.read = MagicMock(
            return_value='asaltedpw'
        )

        mcheckpw.return_value = True
        mencode.return_value = 'mytoken'
        rv = self.application.post('/v1/login', data=dict(
                                   username='admin',
                                   password='password'))
        assert 'mytoken' in rv.data
        mcheckpw.assert_called_with('password', 'asaltedpw')

        # It's hard to test if encode was called with the right paramemters because it calls it
        # with a time based expiration, so we'll just ensure we're encoding here
        mencode.assert_called()
        ms3.head_object.assert_called_with(Bucket='storserv-users', Key='admin')
        ms3.get_object.assert_called_with(Bucket='storserv-users', Key='admin')

    def test


if __name__ == '__main__':
    unittest.main()
