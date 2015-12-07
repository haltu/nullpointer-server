from django import contrib
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from django.contrib.auth import hashers
from models import Playlist, Device, Media
from serializers import DeviceSerializer, MediaSerializer, PlaylistSerializer
import base64


def resp_equals(expected, got):
    for key in expected:
        if key not in got:
            raise Exception('The key: ' + unicode(key) + ' is not in ' +
                            unicode(got))
        if unicode(got[key]) != unicode(expected[key]):
            raise Exception('Expected: ' + unicode(expected[key]) +
                            ', got: ' + unicode(got[key]))
    return True


def set_basic_auth_header(client, username, password):
    credentials = base64.encodestring(username + ':' + password).strip()
    client.credentials(HTTP_AUTHORIZATION='Basic ' + credentials)

class UserTests(APITestCase):
    '''
    Tests posting users and fetching users
    '''
    def setUp(self):
        '''
        Creates some test users
        '''
        self.start_user_count = 10
        for i in range(0, self.start_user_count):
            username = 'user' + str(i)
            password = 'password' + str(i)

            User.objects.create_user(username=username, password=password)
        self.assertEqual(User.objects.count(), self.start_user_count)

    def test_create_user(self):
        """
        Ensure we can create a new user
        """
        url = '/api/user'
        user = {'username': 'test_user', 'password': 'password123'}
        response = self.client.post(url, user, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['username'], user['username'])
        self.assertFalse('password' in response.data)

        self.assertEqual(User.objects.count(), self.start_user_count + 1)
        users = User.objects.all().filter(username=user['username'])
        self.assertEquals(len(users), 1)
        self.assertEqual(users[0].username, user['username'])
        pass_ok = hashers.check_password(user['password'], users[0].password)
        self.assertTrue(pass_ok)

    def test_create_user_bad_data(self):
        '''
        Tests that we get 400 bad request for bad data
        '''
        url = '/api/user'
        user = {'this': None, 'should': None, 'not': None, 'work': None}
        response = self.client.post(url, user, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_find_user(self):
        '''
        Test we can find a user
        '''
        set_basic_auth_header(self.client, 'user0', 'password0')
        url = '/api/user/user0'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['username'], 'user0')
        self.assertFalse('password' in response.data)

    def test_find_missing_user(self):
        '''
        Tests that finding a missing user returns 403
        '''
        #TODO should we return 404 or 403?
        set_basic_auth_header(self.client, 'user0', 'password0')
        url = '/api/user/user_that_does_not_exist'
        response = self.client.get(url)
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class DeviceTest(APITestCase):

    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpass'
        set_basic_auth_header(self.client, self.username, self.password)
        self.owner = User.objects.create_user(username=self.username,
                                              password=self.password)
        self.playlist = Playlist.objects.create(owner=self.owner,
                                                name='test_playlist',
                                                description='test_description',
                                                media_schedule_json='{}')
        self.assertEquals(User.objects.count(), 1)
        self.assertEquals(Playlist.objects.count(), 1)

    def test_add_device(self):
        url = '/api/user/' + self.username + '/device'
        device = {
            'unique_device_id': 'device_1',
            'playlist': self.playlist.id
        }
        response = self.client.post(url, device, format='json')
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.contains_data(response.data, device))
        db_device = Device.objects.get(pk=device['unique_device_id'])
        self.assertEquals(db_device.playlist, self.playlist)
        self.assertEquals(db_device.owner, self.owner)

    def test_add_device_bad_data(self):
        url = '/api/user/' + self.username + '/device'
        device = {
            'bad': 'data',
            'should': 'fail'
        }
        response = self.client.post(url, device, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def contains_data(self, response_data, data):
        for key in data:
            if key not in response_data or not response_data[key] == data[key]:
                return False
        return True

    def test_get_device(self):
        db_device = Device.objects.create(unique_device_id='device_1',
                                          playlist=self.playlist,
                                          owner=self.owner)
        url = '/api/user/' + self.username + '/device/' + \
              db_device.unique_device_id
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        expected_data = DeviceSerializer(db_device).data
        self.assertTrue(resp_equals(expected_data, response.data))

    def test_get_missing_device(self):
        url = '/api/user/' + self.username + '/device/' + 'missing_device'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_devices_for_user(self):
        devices = []
        for i in range(0, 10):
            device = {
                'unique_device_id': 'device_' + str(i),
                'playlist': self.playlist.id
            }
            devices.append(device)

        url = '/api/user/' + self.username + '/device'
        for device in devices:
            self.client.post(url, device, format='json')

        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 10)


class PlaylistTest(APITestCase):

    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpass'
        self.owner = User.objects.create_user(username=self.username,
                                              password=self.password)
        set_basic_auth_header(self.client, self.username, self.password)

    def test_create_playlist(self):
        url = '/api/user/' + self.username + '/playlist'
        playlist = {
            'name': 'Cool playlist',
            'description': 'All the best stuff',
            'media_schedule_json': '{"fake_playlist" : "true"}'
        }
        response = self.client.post(url, playlist, format='json')
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp_equals(playlist, response.data))
        db_playlist = Playlist.objects.get(pk=response.data['id'])
        expected_data = PlaylistSerializer(db_playlist).data
        self.assertTrue(resp_equals(expected_data, response.data))

    def test_create_playlist_bad_data(self):
        url = '/api/user/' + self.username + '/playlist'
        playlist = {
            'this': 'should',
            'not': 'work'
        }
        response = self.client.post(url, playlist, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_playlist_for_missing_user(self):
        url = '/api/user/doesnotexist/playlist'
        playlist = {
            'name': 'Cool playlist',
            'description': 'All the best stuff',
            'media_schedule_json': '{"fake_playlist" : "true"}'
        }
        response = self.client.post(url, playlist, format='json')
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_all_playlists(self):
        playlist_count = 10
        playlists = []
        for i in range(0, playlist_count):
            playlist = {
                'name': 'Cool playlist',
                'description': 'All the best stuff',
                'media_schedule_json': '{"fake_playlist_json" : "true"}'
            }
            playlists.append(playlist)

        url = '/api/user/' + self.username + '/playlist'

        for playlist in playlists:
            response = self.client.post(url, playlist, format='json')
            self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(Playlist.objects.count(), playlist_count)

        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 10)

        for i in range(0, len(response.data)):
            for key in playlists[i]:
                self.assertTrue(key in response.data[i])

    def test_get_all_playlists_for_missing_user(self):
        url = '/api/user/doesnotexist/playlist'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_playlist(self):
        playlist = Playlist.objects.create(
            owner=self.owner,
            name='Cool playlist',
            description='All the best stuff',
            media_schedule_json='{"fake_playlist_json": "true"}'
        )

        self.assertEquals(Playlist.objects.count(), 1)
        url = '/api/user/' + self.username + '/playlist/' + str(playlist.id)

        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        expected_data = PlaylistSerializer(playlist).data
        self.assertTrue(resp_equals(expected_data, response.data))

    def test_get_missing_playlist(self):
        url = '/api/user/' + self.username + '/playlist/13371337'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_playlist_update(self):
        playlist = Playlist.objects.create(
            owner=self.owner,
            name='Cool playlist',
            description='All the best stuff',
            media_schedule_json='{"fake_playlist_json": "true"}'
        )
        self.assertEquals(Playlist.objects.count(), 1)

        url = '/api/user/' + self.username + '/playlist/' + str(playlist.id)
        new_name = 'New name'
        new_description = 'New description'
        new_json = '{"new_playlist":"true"}'
        data = {
            'name': new_name,
            'description': new_description,
            'media_schedule_json': new_json
        }
        response = self.client.put(url, data, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        received = response.data
        self.assertEquals(received['name'], new_name)
        self.assertEquals(received['description'], new_description)
        self.assertEquals(received['media_schedule_json'], new_json)

    def test_put_playlist_update_bad_data(self):
        playlist = Playlist.objects.create(
            owner=self.owner,
            name='Cool playlist',
            description='All the best stuff',
            media_schedule_json='{"fake_playlist_json": "true"}'
        )
        self.assertEquals(Playlist.objects.count(), 1)
        url = '/api/user/' + self.username + '/playlist/' + str(playlist.id)
        data = {
            'this': 'should',
            'not': 'work'
        }
        response = self.client.put(url, data, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_playlist_update_for_missing_playlist(self):
        new_name = 'New name'
        new_description = 'New description'
        new_json = '{"new_playlist":"true"}'
        url = '/api/user/' + self.username + '/13371337'
        data = {
            'name': new_name,
            'description': new_description,
            'media_schedule_json': new_json
        }
        response = self.client.put(url, data, format='json')
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class MediaTestBase(APITestCase):

    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpassword'
        self.owner = User.objects.create_user(username=self.username,
                                              password=self.password)
        self.assertEquals(User.objects.count(), 1)
        set_basic_auth_header(self.client, self.username, self.password)

    def test_post_new_media(self):
        url = '/api/user/' + self.username + '/media'
        media = {
            'url': 'http://cdn3.volusion.com/sbcpn.tjpek/v/vspfiles/photos/FACE001C-2.jpg',
            'media_type' : 'I',
            #'name': 'sad face',
            #'description': 'A big blue sad face',
            #'md5_checksum': 'ac59c6b42a025514e5de073d697b2afb'  # fake
        }
        response = self.client.post(url, media, format='json')
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp_equals(media, response.data))
        db_media = Media.objects.get(pk=response.data['id'])
        expected_db_data = MediaSerializer(db_media).data
        self.assertTrue(resp_equals(expected_db_data, response.data))

    def test_post_new_media_bad_data(self):
        url = '/api/user/' + self.username + '/media'
        media = {
            'this': 'should',
            'not': 'work'
        }
        response = self.client.post(url, media, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_new_media_for_missing_user(self):
        url = '/api/user/notarealuser/media'
        media = {
            'url': 'http://cdn3.volusion.com/sbcpn.tjpek/v/vspfiles/photos/FACE001C-2.jpg',
            'media_type': 'I',
            #'name': 'sad face',
            #'description': 'A big blue sad face',
            #'md5_checksum': 'ac59c6b42a025514e5de073d697b2afb'  # fake
        }
        response = self.client.post(url, media, format='json')
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_media(self):
        url = '/api/user/' + self.username + '/media'
        media = {
            'url': 'http://cdn3.volusion.com/sbcpn.tjpek/v/vspfiles/photos/FACE001C-2.jpg',
            'media_type': 'I',
            #'name': 'sad face',
            #'description': 'A big blue sad face',
            #'md5_checksum': 'ac59c6b42a025514e5de073d697b2afb'  # fake
        }
        response = self.client.post(url, media, format='json')
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        id = response.data['id']
        url = '/api/user/' + self.username + '/media/' + str(id)
        response = self.client.delete(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEquals(Media.objects.count(), 0)

    def test_delete_missing_media(self):
        url = '/api/user/' + self.username + '/media/1337'
        response = self.client.delete(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_media(self):
        media = []
        for i in range(0, 10):
            media_item = {
                'url': 'http://cdn3.volusion.com/sbcpn.tjpek/v/vspfiles/photos/FACE001C-2.jpg',
                'media_type': 'I',
                #'name': 'sad face',
                #'description': 'A big blue sad face',
                #'md5_checksum': 'ac59c6b42a025514e5de073d697b2afb'  # fake
            }
            media.append(media_item)

        url = '/api/user/' + self.username + '/media'
        for media_item in media:
            self.client.post(url, media_item, format='json')

        self.assertEquals(Media.objects.count(), 10)

        response = self.client.get(url, format='json')
        for i in range(0, 10):
            self.assertTrue(resp_equals(media[i], response.data[i]))

    def test_get_all_media_for_missing_user(self):
        url = '/api/user/doesnotexist/media'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_media(self):
        media = Media.objects.create(
            owner=self.owner,
            url='http://cdn3.volusion.com/sbcpn.tjpek/v/vspfiles/photos/FACE001C-2.jpg',
            media_type='I',
            #name='sad face',
            #description='A big blue sad face',
            #md5_checksum='ac59c6b42a025514e5de073d697b2afb'
        )

        self.assertEquals(Media.objects.count(), 1)

        url = '/api/user/' + self.username + '/media/' + str(media.id)
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        expected_data = MediaSerializer(media).data
        self.assertTrue(resp_equals(expected_data, response.data))

    def test_get_missing_media(self):
        url = '/api/user/' + self.username + '/media/13371337'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class DevicePlaylist(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.playlist = Playlist.objects.create(
            owner=self.user,
            name='test name',
            description='test description',
            media_schedule_json='{"fake_json": "true"}'
        )
        self.device = Device.objects.create(
            owner=self.user,
            unique_device_id='testdevice',
            playlist=self.playlist
        )

    def test_get_device_playlist(self):
        url = '/api/device/' + self.device.unique_device_id + '/playlist'

        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        expected = PlaylistSerializer(self.playlist).data
        serializer = PlaylistSerializer(data=response.data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(resp_equals(expected, response.data))

    def test_get_missing_device_playlist(self):
        url = '/api/device/doesnotexist/playlist'
        response = self.client.get(url, format='json')
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)










from django.core.files.uploadedfile import SimpleUploadedFile
import os
import logging
logger = logging.getLogger(__name__)
from hashlib import md5
import json
import tempfile
import shutil
from hisra_server import settings


def get_md5(filePath):
    m = md5()
    with open(filePath,'rb') as f:
        while True:
            chunk = f.read(128)
            if not chunk:
                break
            m.update(chunk)
    return m.hexdigest()


class MediaUploadTestCase(APITestCase):
    def setUp(self):
        self.__real_media_dir = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = tempfile.mkdtemp(suffix='test')

        self.username = 'testuser'
        self.password = 'testpassword'
        self.owner = User.objects.create_user(username=self.username,
                                              password=self.password,id=2000000000)
        self.assertEquals(User.objects.count(), 1)
        self.test_file = 'test_media/kuva.jpg'
        original = open(self.test_file, "rb")
        self.upload_file = SimpleUploadedFile(name="kuva.jpg", content=original.read())
        original.close()

    def test_post_file(self):
        logger.debug("MEDIA ROOT IS: %s", settings.MEDIA_ROOT)
        set_basic_auth_header(self.client, self.username, self.password)
        response = self.client.post('/api/chunked_upload/', {'the_file':self.upload_file})
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        dictResp = json.loads(response.content)
        upload_id = dictResp['upload_id']
        logger.debug(upload_id)
        md5_checksum = get_md5(self.test_file)
        logger.debug(md5_checksum)
        data = {
            'upload_id': upload_id,
            'md5': md5_checksum
        }
        response = self.client.post('/api/chunked_upload_complete/', data=data)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        return json.loads(response.content)
        # for chunk in upload_file.chunks(100):
        #     response = self.client.post('/api/chunked_upload/', {'the_file':chunk})
        #     logger.info("RESPONSE: %s", response)

    def test_get_file_no_authorization(self):
        # create media first
        media = Media.objects.create_media(self.upload_file, self.owner)
        logger.debug("Media id: %s", media.id)
        url = '/media/' + str(media.id)
        # NO auth
        response = self.client.get(url)

        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # note: does not actually return a file because we use web server to do that
    def test_get_file_basic_auth(self):

        media = Media.objects.create_media(self.upload_file, self.owner)
        logger.debug("Media id: %s", media.id)
        url = '/media/' + str(media.id)

        set_basic_auth_header(self.client, self.username, self.password)

        response = self.client.get(url)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        if not response.get('Content-Disposition').startswith("attachment; filename=kuva"):
            raise AssertionError("Content disposition was unexpected")
        if not response.get('X-Accel-Redirect').startswith("/protected/" + str(self.owner.id)):
            raise AssertionError("Content disposition was unexpected")

    # note: does not actually return a file because we use web server to do that
    def test_get_file_owned_device(self):
        Device.objects.create(unique_device_id='device_1', owner=self.owner)

        media = Media.objects.create_media(self.upload_file, self.owner)
        logger.debug("Media id: %s", media.id)

        url = '/media/' + str(media.id) + '?device_id=device_1'

        response = self.client.get(url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        if not response.get('Content-Disposition').startswith("attachment; filename=kuva"):
            raise AssertionError("Content disposition was unexpected")
        if not response.get('X-Accel-Redirect').startswith("/protected/" + str(self.owner.id)):
            raise AssertionError("Content disposition was unexpected")

    def test_get_file_with_filename(self):

        Device.objects.create(unique_device_id='device_1', owner=self.owner)

        media = Media.objects.create_media(self.upload_file, self.owner)
        url = '/media/' + media.media_file.name + '?device_id=device_1'
        #set_basic_auth_header(self.client, self.username, self.password)
        response = self.client.get(url)
        logger.debug(response)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        if not response.get('Content-Disposition').startswith("attachment; filename=kuva"):
            raise AssertionError("Content disposition was unexpected")
        if not response.get('X-Accel-Redirect').startswith("/protected/" + str(self.owner.id)):
            raise AssertionError("Content disposition was unexpected")

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT)
        settings.MEDIA_ROOT = self.__real_media_dir
