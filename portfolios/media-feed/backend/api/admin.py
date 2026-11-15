from django.contrib import admin
from .models import User, Content, Tag, Profile, Following, BookmarkedContent, Bookmark, Comment, Article, ArticleTag, Series, SeriesQueueItem

admin.site.register(User)
admin.site.register(Content)
admin.site.register(Tag)
admin.site.register(Profile)
admin.site.register(Following)
admin.site.register(BookmarkedContent)
admin.site.register(Bookmark)
admin.site.register(Comment)
admin.site.register(Article)
admin.site.register(ArticleTag)
admin.site.register(Series)
admin.site.register(SeriesQueueItem)
