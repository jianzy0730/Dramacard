# Android Client Skeleton

这个目录是短剧互动播放器的安卓客户端骨架。

当前骨架已经预留：

- `Jetpack Compose` 页面结构
- `ExoPlayer` 播放容器
- 本地内容包数据模型
- 高光卡册与结局卡册的基础状态
- 后续接 JSON 内容包的仓库接口

建议开发顺序：

1. 用 Android Studio 打开 `android-client/`
2. 让 Gradle 同步依赖
3. 先跑起空白 App
4. 把 `demo/outputs/...` 的内容整理成客户端消费的内容包
5. 用 `LocalDramaRepository` 接入本地 JSON
6. 再把高光弹层、结局选择、卡册持久化逐步接上

后续准备接入的重点文件：

- `app/src/main/java/com/dramacard/client/data/model/DramaContent.kt`
- `app/src/main/java/com/dramacard/client/data/repo/DramaRepository.kt`
- `app/src/main/java/com/dramacard/client/player/PlayerViewModel.kt`
- `app/src/main/java/com/dramacard/client/player/PlayerScreen.kt`
