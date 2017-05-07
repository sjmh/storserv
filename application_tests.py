import application as flaskr
import unittest
from mock import MagicMock, patch


class FlaskrTestCase(unittest.TestCase):

    def setUp(self):
        flaskr.application.config['TESTING'] = True
        flaskr.application.config['SECRET_KEY'] = 'foo'
        self.application = flaskr.application.test_client()

    def tearDown(self):
        pass

    def testPing(self):
        rv = self.application.get('/v1/ping')
        assert b'pong' in rv.data

    @patch('application.jwt.encode')
    @patch('application.bcrypt.checkpw')
    @patch('application.get_db')
    def testLogin(self, m_db, m_checkpw, m_encode):
        # Mock out s3 calls
        s3 = MagicMock()
        s3.head_object = MagicMock(return_value=True)
        pwhash = MagicMock()
        s3.get_object = MagicMock(return_value={'Body': pwhash})
        m_db.return_value = s3

        # Test a valid login
        pwhash.read = MagicMock(
            return_value='asaltedpw'
        )

        m_checkpw.return_value = True
        m_encode.return_value = 'mytoken'
        rv = self.application.post('/v1/login', data=dict(
                                   username='admin',
                                   password='password'))
        assert 'mytoken' in rv.data
        m_checkpw.assert_called_with('password', 'asaltedpw')

        # It's hard to test if encode was called with the right paramemters because it calls it
        # with a time based expiration, so we'll just ensure we're encoding here
        m_encode.assert_called()
        s3.head_object.assert_called_with(Bucket='storserv-users', Key='admin')
        s3.get_object.assert_called_with(Bucket='storserv-users', Key='admin')


if __name__ == '__main__':
    unittest.main()
