import io
import ipaddress
import logging
import mimetypes
import os
import random
import string
import zipfile
from pathlib import Path

access_logger = logging.getLogger('api.access')
_LAN_SUBNET = ipaddress.ip_network('192.168.1.0/24')


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _is_lan_ip(ip_str: str) -> bool:
    try:
        return ipaddress.ip_address(ip_str) in _LAN_SUBNET
    except ValueError:
        return False


from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Content, Tag, Profile, Following, BookmarkedContent, Bookmark, Comment, ContentDetail, Article, ArticleTag, Series, SeriesQueueItem, ClickCount, UserDetail, Inquiry, AdContentTag, AdContent
from .ranged_response import local_file_response, s3_object_response
from .s3_client import get_s3_client, parse_s3_path
from .serializers import (
    UserRegisterSerializer, ContentSerializer, TagSerializer,
    ProfileSerializer, ProfileUpdateSerializer, FollowingSerializer,
    BookmarkedContentSerializer, CommentSerializer,
    ArticleSerializer, ArticleTagSerializer,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '登録完了'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        detail, _ = UserDetail.objects.get_or_create(user=request.user)
        return Response({
            'username': request.user.username,
            'is_affiliate': detail.is_affiliate,
            'is_uploader': detail.is_uploader,
            'is_author': detail.is_author,
        })


class DeleteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContentListView(generics.ListCreateAPIView):
    serializer_class = ContentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Content.objects.prefetch_related('tags').all()
        params = self.request.query_params

        content_type = params.get('type')
        if content_type:
            qs = qs.filter(type=content_type)

        q = params.get('q')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        tags = params.getlist('tag')
        if tags:
            for tag in tags:
                qs = qs.filter(tags__name=tag)

        user = params.get('user')
        if user:
            qs = qs.filter(user=user)

        exclude_users = params.getlist('exclude_user[]')
        if exclude_users:
            qs = qs.exclude(user__in=exclude_users)

        series_id = params.get('series_id')
        series_number_str = params.get('series_number')
        if series_id is not None:
            if series_number_str is not None:
                try:
                    qs = qs.filter(detail__series__series_id=series_id, detail__series_number=int(series_number_str))
                except ValueError:
                    qs = qs.filter(detail__series__series_id=series_id)
            else:
                qs = qs.filter(detail__series__series_id=series_id)

        if params.get('random') == 'true':
            qs = qs.order_by('?')

        return qs.distinct()
    """
    def list(self, request, *args, **kwargs):
        if request.query_params.get('random') == 'true' and SeriesQueueItem.objects.exists():
            return self._weighted_random_response(request)
        return super().list(request, *args, **kwargs)
    """

    def _weighted_random_response(self, request):
        params = request.query_params
        content_type = params.get('type')
        exclude_user = params.get('exclude_user')
        filter_user = params.get('user')

        def base_qs():
            qs = Content.objects.prefetch_related('tags').all()
            if content_type:
                qs = qs.filter(type=content_type)
            if exclude_user:
                qs = qs.exclude(user=exclude_user)
            if filter_user:
                qs = qs.filter(user=filter_user)
            return qs

        page_size = 20
        queue_items = list(SeriesQueueItem.objects.order_by('?')[:page_size])
        contents = []
        seen_ids = set()
        for item in queue_items:
            sid = item.series_id
            content = (
                base_qs()
                .filter(detail__series__series_id=sid)
                .order_by('?')
                .first()
            )
            if not content:
                content = base_qs().filter(id=sid).first()
            if not content:
                print(f"[SeriesQueue] No content for series_id={sid}")
                continue
            if content.id not in seen_ids:
                seen_ids.add(content.id)
                contents.append(content)
        serializer = self.get_serializer(contents, many=True)
        return Response({'results': serializer.data, 'count': len(contents)})


class ContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Content.objects.prefetch_related('tags').all()
    serializer_class = ContentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class TagListView(generics.ListAPIView):
    queryset = Tag.objects.prefetch_related('contents').all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, username):
        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ProfileSerializer(profile).data)

    def put(self, request, username):
        if request.user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)
        profile = request.user.profile
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProfileSerializer(profile).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookmarkListView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, username):
        try:
            bookmark = Bookmark.objects.get(user__username=username)
        except Bookmark.DoesNotExist:
            return Response([])
        contents = bookmark.contents.filter(is_published=True).select_related('content')
        return Response(BookmarkedContentSerializer(contents, many=True).data)

    def post(self, request, username):
        if request.user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)
        content_id = request.data.get('content_id')
        if not content_id:
            return Response({'error': 'content_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            content = Content.objects.get(id=content_id)
        except Content.DoesNotExist:
            return Response({'error': 'コンテンツが見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        bc, created = BookmarkedContent.objects.get_or_create(content=content, user=request.user)
        bookmark, _ = Bookmark.objects.get_or_create(user=request.user)
        bookmark.contents.add(bc)
        return Response(BookmarkedContentSerializer(bc).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class BookmarkDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, username):
        if request.user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)

        content_ids = request.data.get('content_ids', [])
        if not content_ids:
            return Response({'error': 'content_ids required'}, status=status.HTTP_400_BAD_REQUEST)

        contents = Content.objects.filter(id__in=content_ids)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for content in contents:
                if content.path:
                    filepath = Path(settings.MEDIA_ROOT) / content.path
                    if filepath.exists():
                        zf.write(str(filepath), Path(content.path).name)
                elif content.link:
                    try:
                        import requests as _req
                        resp = _req.get(content.link, timeout=30)
                        resp.raise_for_status()
                        ext = content.link.split('.')[-1].split('?')[0][:10]
                        zf.writestr(f"{content.id}.{ext}", resp.content)
                    except Exception:
                        pass

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="bookmarks.zip"'
        return response


class BookmarkDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, username, bookmark_id):
        if request.user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            bc = BookmarkedContent.objects.get(id=bookmark_id, user=request.user)
        except BookmarkedContent.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        bc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowingListView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, username):
        try:
            following = Following.objects.get(user__username=username)
        except Following.DoesNotExist:
            return Response({'following_users': []})
        return Response(FollowingSerializer(following).data)

    def post(self, request, username):
        if request.user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)
        target_username = request.data.get('target')
        if not target_username:
            return Response({'error': 'target required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = User.objects.get(username=target_username)
        except User.DoesNotExist:
            return Response({'error': 'ユーザーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        following, _ = Following.objects.get_or_create(user=request.user)
        following.following_users.add(target)
        return Response(status=status.HTTP_200_OK)


class FollowingDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, username, target_username):
        if request.user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            following = Following.objects.get(user=request.user)
            target = User.objects.get(username=target_username)
            following.following_users.remove(target)
        except (Following.DoesNotExist, User.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentListView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, content_id):
        comments = Comment.objects.filter(content_id=content_id).select_related('user')
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, content_id):
        try:
            content = Content.objects.get(id=content_id)
        except Content.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(content=content, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get(self, request):
        q = request.query_params.get('q', '')
        profiles = Profile.objects.select_related('user').all()
        if q:
            profiles = profiles.filter(description__icontains=q)
        data = [{'username': p.user.username, 'description': p.description or ''} for p in profiles]
        return Response(data)


class ContentRelatedView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            content = Content.objects.get(id=pk)
        except Content.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        tag_names = list(content.tags.values_list('name', flat=True))
        qs = Content.objects.prefetch_related('tags').exclude(id=pk)

        if tag_names:
            q = Q()
            for tag in tag_names:
                q |= Q(tags__name=tag)
            related = qs.filter(q).distinct().order_by('?')[:20]
            if related.exists():
                return Response({'results': ContentSerializer(related, many=True).data, 'count': related.count()})

        fallback = qs.order_by('?')[:20]
        return Response({'results': ContentSerializer(fallback, many=True).data, 'count': fallback.count()})


class ContentMediaView(APIView):
    """メディア本体を返す。

    HTTP Range に対応しているため、`<video>` は必要な範囲だけを取得でき、
    シークもできる。キャッシュ制御を併せて付けるので、再視聴時は再取得されない。
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            content = Content.objects.get(id=pk)
        except Content.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not content.path:
            return Response(status=status.HTTP_404_NOT_FOUND)

        cache_max_age = getattr(settings, 'MEDIA_CACHE_MAX_AGE', 0)

        parsed = parse_s3_path(content.path)
        if parsed:
            bucket, key = parsed
            try:
                # バケットごとに存在するリージョンが異なりうる（東京への移行期間中）。
                s3 = get_s3_client(bucket=bucket)
                response = s3_object_response(
                    request, s3, bucket, key, cache_max_age=cache_max_age
                )
            except Exception as e:
                return Response(str(e), status=status.HTTP_404_NOT_FOUND)
            if response is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            return response

        filepath = Path(settings.MEDIA_ROOT) / content.path
        if not filepath.exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        return local_file_response(request, filepath, cache_max_age=cache_max_age)


class CommentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id, user=request.user)
        except Comment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id, user=request.user)
        except Comment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _extract_video_thumbnail(content, article_title, article_description, user):
    """動画の中間フレームを画像として保存し、Contentモデルとして返す"""
    from django.conf import settings
    try:
        import cv2
    except ImportError:
        return None

    video_path = os.path.join(settings.MEDIA_ROOT, content.path)
    if not os.path.exists(video_path):
        return None

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None

    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    filename = f"thumb_{rand_suffix}.jpg"
    save_dir = os.path.join(settings.MEDIA_ROOT, 'images')
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    ret2, buf = cv2.imencode('.jpg', frame)
    if not ret2:
        return None
    with open(save_path, 'wb') as f:
        f.write(buf.tobytes())

    relative_path = f"images/{filename}"
    thumb_content = Content(
        type=Content.TYPE_IMAGE,
        title=f"{article_title}-サムネイル",
        path=relative_path,
        source_url=content.source_url,
        user=user.username,
        description=article_description,
    )
    thumb_content.save()
    return thumb_content


class ArticleListView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = Article.objects.prefetch_related('contents', 'article_tags').select_related('thumbnail', 'user').all()
        q = request.query_params.get('q')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        tag = request.query_params.get('tag')
        if tag:
            qs = qs.filter(article_tags__name=tag)
        count = qs.count()
        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = max(int(request.query_params.get('page_size', 20)), 1)
        start = (page - 1) * page_size
        qs = qs[start:start + page_size]
        serializer = ArticleSerializer(qs, many=True)
        return Response({'results': serializer.data, 'count': count})

    def post(self, request):
        data = request.data.copy()
        content_ids = data.get('content_ids', [])
        title = data.get('title', '')
        description = data.get('description', '')

        # サムネイル自動決定
        thumbnail_id = data.get('thumbnail_id')
        if not thumbnail_id and content_ids:
            contents = list(Content.objects.filter(id__in=content_ids))
            images = [c for c in contents if c.type == Content.TYPE_IMAGE]
            videos = [c for c in contents if c.type == Content.TYPE_VIDEO]
            if images:
                thumbnail_id = random.choice(images).id
            elif videos:
                chosen_video = random.choice(videos)
                thumb = _extract_video_thumbnail(chosen_video, title, description, request.user)
                if thumb:
                    thumbnail_id = thumb.id
                    content_ids = list(content_ids) + [thumb.id]

        data = data.copy()
        if thumbnail_id:
            data['thumbnail_id'] = thumbnail_id

        serializer = ArticleSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _process_click(affiliate_username, t_str, ip, referrer, page_link):
    import time
    from django.utils import timezone
    from datetime import timedelta

    # 5秒以上経過チェック
    try:
        elapsed = time.time() - int(t_str)
        if elapsed < 5:
            return
    except (ValueError, TypeError):
        return

    # 同IP短時間多発チェック（10分以内に5件以上は無効）
    recent_cutoff = timezone.now() - timedelta(minutes=10)
    recent_count = ClickCount.objects.filter(ip_address=ip, created_at__gte=recent_cutoff).count()
    if recent_count >= 5:
        return

    try:
        user = User.objects.get(username=affiliate_username)
    except User.DoesNotExist:
        return

    ClickCount.objects.create(
        user=user,
        referrer=referrer or '',
        page_link=page_link,
        ip_address=ip,
    )


class ArticleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        try:
            article = Article.objects.prefetch_related('contents', 'article_tags').select_related('thumbnail', 'user').get(pk=pk)
        except Article.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        affiliate_username = request.query_params.get('affiliate_user_id')
        t_str = request.query_params.get('t')
        if affiliate_username and t_str:
            import threading
            ip = _get_client_ip(request)
            referrer = request.META.get('HTTP_REFERER', '')
            page_link = request.build_absolute_uri(request.path)
            thread = threading.Thread(
                target=_process_click,
                args=(affiliate_username, t_str, ip, referrer, page_link),
                daemon=True,
            )
            thread.start()

        return Response(ArticleSerializer(article).data)

    def delete(self, request, pk):
        try:
            article = Article.objects.get(pk=pk, user=request.user)
        except Article.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArticleTagListView(generics.ListAPIView):
    queryset = ArticleTag.objects.all().order_by('name')
    serializer_class = ArticleTagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class BlogPartsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        import time as _time
        cols = int(request.query_params.get('cols', 3))
        rows = int(request.query_params.get('rows', 3))
        keyword = request.query_params.get('keyword', '')
        color = request.query_params.get('color', '#1a1a2e')
        font_color = request.query_params.get('font_color', '#ffffff')
        tile_size = int(request.query_params.get('tile_size', 150))
        site_url = request.query_params.get('site_url', 'http://localhost:3000').rstrip('/')
        affiliate_user_id = request.query_params.get('affiliate_user_id', '')
        t = int(_time.time())

        qs = Article.objects.select_related('thumbnail').all()
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))

        limit = cols * rows
        articles = list(qs[:limit])

        from django.conf import settings
        media_base = request.build_absolute_uri(settings.MEDIA_URL)

        img_h = int(tile_size * 0.7)
        title_h = tile_size - img_h

        cells = []
        for article in articles:
            thumb_url = ''
            if article.thumbnail:
                if article.thumbnail.path:
                    thumb_url = f"{media_base}{article.thumbnail.path}"
                elif article.thumbnail.link:
                    thumb_url = article.thumbnail.link

            img_html = (
                f'<img src="{thumb_url}" style="width:100%;height:100%;object-fit:cover;display:block;" />'
                if thumb_url
                else '<div style="width:100%;height:100%;background:#333;"></div>'
            )

            article_url = f"{site_url}/articles/{article.id}/"
            if affiliate_user_id:
                article_url += f"?affiliate_user_id={affiliate_user_id}&t={t}"
            cells.append(f'''<a href="{article_url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;display:inline-block;vertical-align:top;margin:4px;flex-shrink:0;">
  <div style="width:{tile_size}px;height:{tile_size}px;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.5);cursor:pointer;">
    <div style="width:{tile_size}px;height:{img_h}px;overflow:hidden;">{img_html}</div>
    <div style="width:{tile_size}px;height:{title_h}px;background:{color};display:flex;align-items:center;justify-content:center;box-sizing:border-box;padding:4px 8px;">
      <span style="color:{font_color};font-size:12px;font-weight:bold;text-align:center;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-all;">{article.title}</span>
    </div>
  </div>
</a>''')

        total_w = cols * (tile_size + 8)
        html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>body{{margin:0;padding:8px;background:#111;font-family:sans-serif;}}a:hover div{{opacity:0.85;}}</style></head>
<body>
<div style="display:flex;flex-wrap:wrap;width:{total_w}px;">
{''.join(cells)}
</div>
</body>
</html>'''

        return HttpResponse(html, content_type='text/html; charset=utf-8')


class ClickCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        qs = ClickCount.objects.filter(user=request.user)
        period = request.query_params.get('period', '')
        if period == 'today':
            qs = qs.filter(created_at__date=timezone.now().date())
        elif period == '7days':
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif period == '30days':
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=30))
        count = qs.count()
        items = list(qs.order_by('-created_at')[:200])
        results = [
            {
                'id': item.id,
                'created_at': item.created_at.isoformat(),
                'referrer': item.referrer,
                'page_link': item.page_link,
                'ip_address': item.ip_address,
            }
            for item in items
        ]
        return Response({'count': count, 'results': results})


class InquiryView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        name = request.data.get('name', '').strip()
        title = request.data.get('title', '').strip()
        email = request.data.get('email', '').strip()
        content = request.data.get('content', '').strip()
        if not all([name, title, email, content]):
            return Response({'error': '全ての項目を入力してください'}, status=status.HTTP_400_BAD_REQUEST)

        inquiry = Inquiry.objects.create(name=name, title=title, email=email, content=content)

        from django.conf import settings as django_settings
        from django.core.mail import send_mail
        recipient = django_settings.INQUIRY_RECIPIENT_EMAIL
        if recipient:
            try:
                send_mail(
                    subject=f'【お問い合わせ】{title}',
                    message=(
                        f'名前: {name}\n'
                        f'メールアドレス: {email}\n'
                        f'タイトル: {title}\n\n'
                        f'内容:\n{content}'
                    ),
                    from_email=django_settings.EMAIL_HOST_USER,
                    recipient_list=[recipient],
                    fail_silently=True,
                )
            except Exception:
                pass

        return Response({'id': inquiry.id}, status=status.HTTP_201_CREATED)


class AdContentListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = AdContent.objects.prefetch_related('tags').all()

        tag_names = request.query_params.getlist('tag')
        if tag_names:
            qs = qs.filter(tags__name__in=tag_names).distinct()

        if request.query_params.get('random') == 'true':
            qs = qs.order_by('?')

        number = request.query_params.get('number')
        if number:
            try:
                qs = qs[:int(number)]
            except (ValueError, TypeError):
                pass

        data = [{'id': a.id, 'html': a.html, 'width': a.width, 'height': a.height, 'tags': [t.name for t in a.tags.all()]} for a in qs]
        return Response(data)


class TurnstileVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        ip = _get_client_ip(request)
        if _is_lan_ip(ip):
            access_logger.info('lan_bypass ip=%s path=/auth/turnstile/', ip)
            return Response({'success': True})
        """

        token = request.data.get('token')
        print("turnstile",ip,_is_lan_ip(ip),token)
        if not token:
            return Response({'success': False, 'error': 'No token'}, status=status.HTTP_400_BAD_REQUEST)
        from django.conf import settings as django_settings
        secret = django_settings.CLOUDFLARE_TURNSTILE_SECRET_KEY
        import requests as _req
        resp = _req.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': secret,
                'response': token,
                'remoteip': ip,
            },
            timeout=10,
        )
        result = resp.json()
        if result.get('success'):
            access_logger.info('turnstile_verified ip=%s', ip)
            return Response({'success': True})
        return Response(
            {'success': False, 'error': result.get('error-codes', [])},
            status=status.HTTP_400_BAD_REQUEST,
        )
