from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/user/', views.DeleteUserView.as_view(), name='delete_user'),
    path('auth/turnstile/', views.TurnstileVerifyView.as_view(), name='turnstile_verify'),
    path('auth/me/', views.UserMeView.as_view(), name='user_me'),
    path('click-counts/', views.ClickCountView.as_view(), name='click_counts'),
    path('inquiries/', views.InquiryView.as_view(), name='inquiry'),

    path('contents/', views.ContentListView.as_view(), name='content_list'),
    path('contents/<str:pk>/', views.ContentDetailView.as_view(), name='content_detail'),
    path('contents/<str:pk>/media/', views.ContentMediaView.as_view(), name='content_media'),
    path('contents/<str:pk>/related/', views.ContentRelatedView.as_view(), name='content_related'),

    path('tags/', views.TagListView.as_view(), name='tag_list'),
    path('users/', views.UserListView.as_view(), name='user_list'),

    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),

    path('bookmarks/<str:username>/', views.BookmarkListView.as_view(), name='bookmark_list'),
    path('bookmarks/<str:username>/download/', views.BookmarkDownloadView.as_view(), name='bookmark_download'),
    path('bookmarks/<str:username>/<str:bookmark_id>/', views.BookmarkDetailView.as_view(), name='bookmark_detail'),

    path('following/<str:username>/', views.FollowingListView.as_view(), name='following_list'),
    path('following/<str:username>/<str:target_username>/', views.FollowingDetailView.as_view(), name='following_detail'),

    path('comments/<str:content_id>/', views.CommentListView.as_view(), name='comment_list'),
    path('comments/detail/<int:comment_id>/', views.CommentDetailView.as_view(), name='comment_detail'),

    path('articles/', views.ArticleListView.as_view(), name='article_list'),
    path('articles/<int:pk>/', views.ArticleDetailView.as_view(), name='article_detail'),
    path('article-tags/', views.ArticleTagListView.as_view(), name='article_tag_list'),
    path('blog-parts/', views.BlogPartsView.as_view(), name='blog_parts'),
    path('ad-contents/', views.AdContentListView.as_view(), name='ad_content_list'),
]
