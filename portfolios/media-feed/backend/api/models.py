import hashlib
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, username, password=None):
        user = self.model(username=username)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None):
        user = self.create_user(username, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True, primary_key=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'ユーザー'

    def __str__(self):
        return self.username


class Content(models.Model):
    TYPE_IMAGE = 'image'
    TYPE_VIDEO = 'video'
    TYPE_CHOICES = [(TYPE_IMAGE, '画像'), (TYPE_VIDEO, '動画')]

    id = models.CharField(max_length=64, primary_key=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    title = models.CharField(max_length=500, blank=True)
    path = models.CharField(max_length=1000, blank=True)
    link = models.URLField(max_length=2000, blank=True)
    source_url = models.URLField(max_length=2000, blank=True)
    user = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'コンテンツ'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            raw = f"{self.path}{self.link}{self.title}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:32]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or self.id


class Tag(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    contents = models.ManyToManyField(Content, related_name='tags', blank=True)

    class Meta:
        verbose_name = 'タグ'

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    description = models.TextField(blank=True, max_length=800)

    class Meta:
        verbose_name = 'プロフィール'

    def __str__(self):
        return f"{self.user.username}のプロフィール"


class Following(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='following')
    following_users = models.ManyToManyField(User, related_name='followers', blank=True)

    class Meta:
        verbose_name = 'フォロー'

    def __str__(self):
        return f"{self.user.username}のフォロー"


class BookmarkedContent(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='bookmarked_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarked_contents')
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'ブックマーク中コンテンツ'
        unique_together = ('content', 'user')

    def save(self, *args, **kwargs):
        if not self.id:
            raw = f"{self.content_id}{self.user_id}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:32]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} -> {self.content_id}"


class Bookmark(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='bookmark')
    contents = models.ManyToManyField(BookmarkedContent, related_name='bookmarks', blank=True)

    class Meta:
        verbose_name = 'ブックマーク'

    def __str__(self):
        return f"{self.user.username}のブックマーク"


class Series(models.Model):
    series_id = models.CharField(max_length=100, primary_key=True)
    weight = models.FloatField(default=10)

    class Meta:
        verbose_name = 'シリーズ'

    def __str__(self):
        return self.series_id


class SeriesQueueItem(models.Model):
    series_id = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'シリーズキューアイテム'

    def __str__(self):
        return self.series_id


class ContentDetail(models.Model):
    content = models.OneToOneField(Content, on_delete=models.CASCADE, primary_key=True, related_name='detail')
    series = models.ForeignKey(Series, on_delete=models.SET_NULL, null=True, blank=True, related_name='content_details')
    series_number = models.IntegerField(default=-1)

    class Meta:
        verbose_name = 'コンテンツ詳細'

    def __str__(self):
        sid = self.series.series_id if self.series else '-1'
        return f"{self.content_id} (series:{sid}/{self.series_number})"


class Article(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    contents = models.ManyToManyField(Content, related_name='articles', blank=True)
    thumbnail = models.ForeignKey(Content, on_delete=models.SET_NULL, null=True, blank=True, related_name='thumbnail_of')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '記事'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ArticleTag(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    articles = models.ManyToManyField(Article, related_name='article_tags', blank=True)

    class Meta:
        verbose_name = '記事タグ'

    def __str__(self):
        return self.name


class Comment(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'コメント'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.text[:30]}"


class ClickCount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='click_counts')
    created_at = models.DateTimeField(auto_now_add=True)
    referrer = models.URLField(max_length=500, blank=True)
    page_link = models.URLField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'クリック数'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_id} -> {self.page_link} ({self.created_at})"


class UserDetail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='user_detail')
    is_affiliate = models.BooleanField(default=False)
    is_uploader = models.BooleanField(default=False)
    is_author = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'ユーザー詳細'

    def __str__(self):
        return f"{self.user_id} (affiliate={self.is_affiliate}, uploader={self.is_uploader}, author={self.is_author})"


@receiver(post_save, sender=User)
def create_user_detail(sender, instance, created, **kwargs):
    if created:
        UserDetail.objects.get_or_create(user=instance)


class Inquiry(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    email = models.EmailField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'お問い合わせ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name}: {self.title}"


class AdContentTag(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    contents = models.ManyToManyField('AdContent', related_name='tags', blank=True)

    class Meta:
        verbose_name = '広告コンテンツタグ'

    def __str__(self):
        return self.name


class AdContent(models.Model):
    html = models.TextField()
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = '広告コンテンツ'

    def __str__(self):
        return f"AdContent {self.id}"
