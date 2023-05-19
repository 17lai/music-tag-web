from rest_framework import serializers


class FileListSerializer(serializers.Serializer):
    file_path = serializers.CharField(required=True)


class Id3Serializer(serializers.Serializer):
    file_path = serializers.CharField(required=True)
    file_name = serializers.CharField(required=True)


class MusicId3Serializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    artist = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    album = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    genre = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    year = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    lyrics = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    is_save_lyrics_file = serializers.BooleanField(required=True)
    comment = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    album_img = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    filename = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    file_full_path = serializers.CharField(required=True)


class UpdateId3Serializer(serializers.Serializer):
    music_id3_info = MusicId3Serializer(many=True)


class BatchUpdateId3Serializer(serializers.Serializer):
    file_full_path = serializers.JSONField(required=True)
    music_info = serializers.JSONField(required=True)
    select_data = serializers.JSONField(required=True)


class FetchId3ByTitleSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    resource = serializers.CharField(required=True)


class FetchLlyricSerializer(serializers.Serializer):
    song_id = serializers.CharField(required=True)
    resource = serializers.CharField(required=True)


class MergeArtistSerializer(serializers.Serializer):
    full_text = serializers.CharField(required=True)
