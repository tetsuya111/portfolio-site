from rest_framework import serializers

from .media_url import resolve_media_url, resolve_poster_url
from .models import User, Content, Tag, Profile, Following, BookmarkedContent, Bookmark, Comment, ContentDetail, Article, ArticleTag, Series, SeriesQueueItem


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user)
        Following.objects.create(user=user)
        Bookmark.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class TagSerializer(serializers.ModelSerializer):
    content_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['name', 'content_count']

    def get_content_count(self, obj):
        return obj.contents.count()


class TagNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']


class ContentDetailSerializer(serializers.ModelSerializer):
    series_id = serializers.SerializerMethodField()

    class Meta:
        model = ContentDetail
        fields = ['series_id', 'series_number']

    def get_series_id(self, obj):
        return obj.series.series_id if obj.series else '-1'


class ContentSerializer(serializers.ModelSerializer):
    tags = TagNameSerializer(many=True, read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    detail = ContentDetailSerializer(read_only=True)
    # 配信URLを一覧のレスポンスに同梱する。URL取得のための往復を増やさないため。
    media_url = serializers.SerializerMethodField()
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = ['id', 'type', 'title', 'path', 'link', 'source_url', 'user', 'description', 'tags', 'tag_names', 'detail', 'created_at', 'media_url', 'poster_url']
        read_only_fields = ['id', 'created_at']

    def get_media_url(self, obj):
        # None のときフロントは従来のアプリ経由URLにフォールバックする。
        return resolve_media_url(obj)

    def get_poster_url(self, obj):
        return resolve_poster_url(obj)

    def create(self, validated_data):
        tag_names = validated_data.pop('tag_names', [])
        content = Content.objects.create(**validated_data)
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag.contents.add(content)
        return content


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Profile
        fields = ['username', 'description']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['description']


class FollowingSerializer(serializers.ModelSerializer):
    following_users = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Following
        fields = ['following_users']


class BookmarkedContentSerializer(serializers.ModelSerializer):
    content = ContentSerializer(read_only=True)
    content_id = serializers.CharField(write_only=True)

    class Meta:
        model = BookmarkedContent
        fields = ['id', 'content', 'content_id', 'is_published']
        read_only_fields = ['id']


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'username', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'username', 'created_at', 'updated_at']


class ArticleTagNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleTag
        fields = ['name']


class ArticleSerializer(serializers.ModelSerializer):
    article_tags = ArticleTagNameSerializer(many=True, read_only=True)
    article_tag_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    content_ids = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    thumbnail_id = serializers.CharField(write_only=True, required=False, allow_null=True)
    thumbnail = ContentSerializer(read_only=True)
    contents = ContentSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'description', 'username',
            'contents', 'content_ids',
            'thumbnail', 'thumbnail_id',
            'article_tags', 'article_tag_names',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'username']

    def create(self, validated_data):
        tag_names = validated_data.pop('article_tag_names', [])
        content_ids = validated_data.pop('content_ids', [])
        thumbnail_id = validated_data.pop('thumbnail_id', None)

        if thumbnail_id:
            try:
                validated_data['thumbnail'] = Content.objects.get(id=thumbnail_id)
            except Content.DoesNotExist:
                pass

        article = Article.objects.create(**validated_data)

        for cid in content_ids:
            try:
                article.contents.add(Content.objects.get(id=cid))
            except Content.DoesNotExist:
                pass

        for name in tag_names:
            tag, _ = ArticleTag.objects.get_or_create(name=name)
            tag.articles.add(article)

        return article


class ArticleTagSerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()

    class Meta:
        model = ArticleTag
        fields = ['name', 'article_count']

    def get_article_count(self, obj):
        return obj.articles.count()
