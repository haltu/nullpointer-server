from rest_framework import serializers
from hisra_models.models import Media,Playlist,RotationPair,Device

class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ('id', 'uri', 'mediatype')

class PlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = ('id', 'name', 'rotation')

class RotationPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotationPair
        fields = ('id', 'media', 'rotationTime')

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('id', 'media', 'playlist')

