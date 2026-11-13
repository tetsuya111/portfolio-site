# 概要
spotifyでspotify APIを使用し、ビルボードに掲載されている曲を含めたアルバムを作成したい。

# 要件
## バッチ
- 任意のbillboardのURLから曲名の一覧を取得できるバッチを作成する
  - スクレイピングする
## バックエンド
- バッチを使用し曲名の一覧を取得し返却できる
- spotifyのoauth認証に対応できる
- 曲名の一覧からspotifyのアルバムを作成できる
## フロントエンド
- テキストボックスにURLを入力できる
- spotifyのoauth認証に対応できる
- ボタンを押下すると入力されたURLからspotifyのアルバムを作成できる
# 設計
- バッチ処理とバックエンドはpython/fast apiを使用する
- フロントエンドはnode/react/nextを使用する
- プロジェクトの作成時は以下のURLを参考にする
  - https://billboard.mryogaku.com/#google_vignette
## 画面
- タイトル
- spotify認証済みか
  - 認証済みならユーザー名などを表示
- URLを入力するテキストボックス
- アルバム作成を実行するボタン
## billboardの曲名の取得先
https://billboard.mryogaku.com/#google_vignette

## 流れ
### バッチ処理
- DBに登録されたURLをスクレイピングし曲名の一覧を取得する
- 曲名の一覧を返却する
### バックエンド
- 基本はフロントエンドの要求に応じる
- フロントエンドとバッチ処理の仲介などをする
### フロントエンド
- 曲名の一覧を取得する
- spotifyのoauth認証をする
- 曲名の一覧からspotifyのアルバムを作成する
# 参考
building with ai : [https://developer.spotify.com/documentation/web-api/tutorials/building-with-ai](https://developer.spotify.com/documentation/web-api/tutorials/building-with-ai)
add playlist : [https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist](https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist)
search : [https://developer.spotify.com/documentation/web-api/reference/search](https://developer.spotify.com/documentation/web-api/reference/search)