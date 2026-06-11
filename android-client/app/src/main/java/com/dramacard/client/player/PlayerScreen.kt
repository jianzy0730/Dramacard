package com.dramacard.client.player

import android.content.Intent
import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import android.webkit.WebView
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.AlertDialog
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.dramacard.client.data.model.CardCategory
import com.dramacard.client.data.model.CollectionCard
import com.dramacard.client.data.model.EndingBranch
import com.dramacard.client.data.model.EpisodeContent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.URL
import kotlin.math.roundToLong

private const val PublicCosBaseUrl = "https://example.com/dramacard-assets"
private const val XingdeAssetBaseUrl =
    "$PublicCosBaseUrl/%E5%B9%B8%E5%BE%97%E7%9B%B8%E9%81%87%E7%A6%BB%E5%A9%9A%E6%97%B6"
private const val HighlightCardBackUrl = "$PublicCosBaseUrl/%E5%8D%A1%E8%83%8C.png"
private const val EndingCardBackUrl = "$PublicCosBaseUrl/ending_card_back.png"
private const val SplashScreenAssetUrl = "asset://splash_screen.jpg"
private const val DiscoveryAssetBaseUrl = "$PublicCosBaseUrl/%E5%B0%81%E9%9D%A2"
private const val CoverYunmiaoUrl = "$DiscoveryAssetBaseUrl/%E4%BA%91%E6%B8%BA.jpg"
private const val CoverBeiwangUrl = "$DiscoveryAssetBaseUrl/%E5%8C%97%E5%BE%80.jpg"
private const val CoverBeipaiUrl = "$DiscoveryAssetBaseUrl/%E5%8C%97%E6%B4%BE%E5%AF%BB%E5%AE%9D%E7%AC%94%E8%AE%B0.jpg"
private const val CoverTainainaiUrl = "$DiscoveryAssetBaseUrl/%E5%8D%81%E5%85%AB%E5%B2%81%E5%A4%AA%E5%A5%B6%E5%A5%B6.jpg"
private const val CoverWankuUrl = "$DiscoveryAssetBaseUrl/%E5%A4%A9%E4%B8%8B%E7%AC%AC%E4%B8%80%E7%BA%A8%E7%BB%94.jpg"
private const val CoverJialijiawaiUrl = "$DiscoveryAssetBaseUrl/%E5%AE%B6%E9%87%8C%E5%AE%B6%E5%A4%96.jpg"
private const val CoverXingdeUrl = "$DiscoveryAssetBaseUrl/%E5%B9%B8%E5%BE%97%E7%9B%B8%E9%81%87%E7%A6%BB%E5%A9%9A%E6%97%B6.jpg"
private const val CoverSiyeUrl = "$DiscoveryAssetBaseUrl/%E6%92%95%E5%A4%9C.jpg"
private const val CoverHuangnianUrl = "$DiscoveryAssetBaseUrl/%E8%8D%92%E5%B9%B4.jpg"
private const val CoverDongzhiUrl = "$DiscoveryAssetBaseUrl/%E9%82%A3%E5%B9%B4%E5%86%AC%E8%87%B3.jpg"
private enum class AppTab(val label: String) {
    Home("首页"),
    Discover("发现"),
    Battle("PK"),
    Collection("卡册"),
    Profile("我的"),
}

private data class DramaShelfItem(
    val title: String,
    val subtitle: String,
    val coverUrl: String = "",
    val episodeCount: Int,
)

private data class CachedImage(
    val bitmap: ImageBitmap,
    val bytes: Int,
)

private object ImageMemoryCache {
    val images = mutableStateMapOf<String, CachedImage>()

    val count: Int
        get() = images.size

    val totalBytes: Int
        get() = images.values.sumOf { it.bytes }

    fun clear() {
        images.clear()
    }
}

private enum class CollectionDetailTab {
    Home,
    Highlight,
    Ending,
}

private enum class ProfileDetailTab {
    Home,
    History,
}

@Composable
private fun AppSplashScreen(
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier.background(Color.Black),
        contentAlignment = Alignment.Center,
    ) {
        RemoteImage(
            imageUrl = SplashScreenAssetUrl,
            contentDescription = "响当当短剧开屏",
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )
    }
}

private data class PlayerColors(
    val background: Color,
    val surface: Color,
    val surfaceAlt: Color,
    val surfaceRaised: Color,
    val text: Color,
    val muted: Color,
    val border: Color,
    val chip: Color,
    val nav: Color,
    val navSelected: Color,
)

private val LightPlayerColors = PlayerColors(
    background = Color(0xFFF6F7FB),
    surface = Color(0xFFFFFFFF),
    surfaceAlt = Color(0xFFF0F3FA),
    surfaceRaised = Color(0xFFFFFFFF),
    text = Color(0xFF172033),
    muted = Color(0xFF374151),
    border = Color(0x52172033),
    chip = Color(0xFFE8ECF5),
    nav = Color(0xF7FFFFFF),
    navSelected = Color(0xFFFFF1C7),
)

private val DarkPlayerColors = PlayerColors(
    background = Color(0xFF05070D),
    surface = Color(0xFF101A31),
    surfaceAlt = Color(0xFF0D1528),
    surfaceRaised = Color(0xFF111C34),
    text = Color.White,
    muted = Color(0xFF9FB0D0),
    border = Color(0x1FFFFFFF),
    chip = Color(0x1AFFFFFF),
    nav = Color(0xF1081020),
    navSelected = Color(0x1AD99000),
)

private val LocalPlayerColors = staticCompositionLocalOf { LightPlayerColors }

@Composable
fun PlayerRoute(
    modifier: Modifier = Modifier,
    viewModel: PlayerViewModel = viewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    PlayerScreen(
        state = state,
        onSelectEpisode = viewModel::selectEpisode,
        onSelectDrama = viewModel::selectDrama,
        onOpenDramaEpisode = viewModel::openDramaEpisode,
        onNextDrama = viewModel::nextDrama,
        onPreviousDrama = viewModel::previousDrama,
        onPreviewHighlight = viewModel::previewHighlight,
        onCollectHighlight = viewModel::collectHighlightCard,
        onPreviewEndingChoice = viewModel::previewEndingChoice,
        onChooseEndingBranch = viewModel::chooseEndingBranch,
        onCastVote = viewModel::castVote,
        onToggleLike = viewModel::toggleLikeCurrentEpisode,
        onToggleFavorite = viewModel::toggleFavoriteCurrentDrama,
        onUpdateProfileAvatar = viewModel::updateProfileAvatar,
        onUpdateProfileName = viewModel::updateProfileName,
        onDismissOverlay = viewModel::dismissOverlay,
        modifier = modifier,
    )
}

@Composable
fun PlayerScreen(
    state: PlayerUiState,
    onSelectEpisode: (EpisodeContent) -> Unit,
    onSelectDrama: (String) -> Unit,
    onOpenDramaEpisode: (String, String?) -> Unit,
    onNextDrama: () -> Unit,
    onPreviousDrama: () -> Unit,
    onPreviewHighlight: (String) -> Unit,
    onCollectHighlight: (CollectionCard) -> Unit,
    onPreviewEndingChoice: () -> Unit,
    onChooseEndingBranch: (EndingBranch) -> Unit,
    onCastVote: (String) -> Unit,
    onToggleLike: () -> Unit,
    onToggleFavorite: () -> Unit,
    onUpdateProfileAvatar: (String?) -> Unit,
    onUpdateProfileName: (String) -> Unit,
    onDismissOverlay: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val drama = state.drama
    val currentEpisode = state.currentEpisode
    val collectionExpanded = remember { mutableStateOf(false) }
    val battleExpanded = remember { mutableStateOf(false) }
    var previewHighlightAction by remember { mutableStateOf<(() -> Unit)?>(null) }
    var previewEndingAction by remember { mutableStateOf<(() -> Unit)?>(null) }
    var selectedCollectionCard by remember { mutableStateOf<CollectionCard?>(null) }
    var activeTab by remember { mutableStateOf(AppTab.Home) }
    var isPlayerFullscreen by remember { mutableStateOf(false) }
    var isEpisodePickerExpanded by remember { mutableStateOf(false) }
    var isLightTheme by remember { mutableStateOf(true) }
    var showSplashScreen by remember { mutableStateOf(true) }
    val controlsVisible = remember { mutableStateOf(true) }
    val controlsInteractionAt = remember { mutableLongStateOf(System.currentTimeMillis()) }

    fun revealControls() {
        controlsVisible.value = true
        controlsInteractionAt.longValue = System.currentTimeMillis()
    }

    LaunchedEffect(state.overlayState) {
        if (state.overlayState != OverlayState.None) {
            collectionExpanded.value = false
            battleExpanded.value = false
            isEpisodePickerExpanded = false
            revealControls()
        }
    }

    LaunchedEffect(Unit) {
        delay(3000)
        showSplashScreen = false
        revealControls()
    }

    LaunchedEffect(activeTab, state.overlayState, controlsInteractionAt.longValue) {
        if (activeTab != AppTab.Home || state.overlayState != OverlayState.None) {
            controlsVisible.value = true
            return@LaunchedEffect
        }
        delay(2600)
        if (activeTab == AppTab.Home &&
            state.overlayState == OverlayState.None &&
            System.currentTimeMillis() - controlsInteractionAt.longValue >= 2500
        ) {
            controlsVisible.value = false
        }
    }

    LaunchedEffect(activeTab) {
        if (activeTab != AppTab.Home) {
            isPlayerFullscreen = false
            isEpisodePickerExpanded = false
        }
    }

    LaunchedEffect(controlsVisible.value, isPlayerFullscreen) {
        if (!controlsVisible.value || isPlayerFullscreen) {
            isEpisodePickerExpanded = false
        }
    }

    fun playNextEpisodeOrDrama() {
        val episodes = drama?.episodes.orEmpty()
        val currentIndex = episodes.indexOfFirst { it.videoPath == currentEpisode?.videoPath }
        val nextEpisode = episodes.getOrNull(currentIndex + 1)
        if (nextEpisode != null) {
            onSelectEpisode(nextEpisode)
        } else {
            onNextDrama()
        }
    }

    CompositionLocalProvider(
        LocalPlayerColors provides if (isLightTheme) LightPlayerColors else DarkPlayerColors
    ) {
    val density = LocalDensity.current
    val navigationBarInset = with(density) { WindowInsets.navigationBars.getBottom(this).toDp() }
    val bottomNavHeight = 68.dp
    var measuredBottomNavHeight by remember { mutableStateOf(0.dp) }
    val estimatedBottomNavOffset = bottomNavHeight + navigationBarInset
    val bottomNavOffset = measuredBottomNavHeight.takeIf { it > 0.dp } ?: estimatedBottomNavOffset
    val bottomContentPadding = bottomNavOffset + 12.dp
    val playerBottomPadding = 126.dp
    val bottomSheetBottomGap = bottomNavOffset
    val bottomSheetContentPadding = 8.dp
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(LocalPlayerColors.current.background)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = if (isPlayerFullscreen) 0.dp else 20.dp),
        ) {
            when (activeTab) {
                AppTab.Home -> {
                    if (!isPlayerFullscreen) {
                        Box(
                            modifier = Modifier.height(68.dp),
                            contentAlignment = Alignment.BottomCenter,
                        ) {
                            if (controlsVisible.value) {
                                EpisodePicker(
                                    episodes = drama?.episodes.orEmpty(),
                                    currentEpisode = currentEpisode,
                                    onToggleExpanded = {
                                        revealControls()
                                        isEpisodePickerExpanded = !isEpisodePickerExpanded
                                    },
                                    onSelectEpisode = {
                                        revealControls()
                                        isEpisodePickerExpanded = false
                                        onSelectEpisode(it)
                                    },
                                )
                            }
                        }
                        Spacer(modifier = Modifier.weight(1f))
                    }
                    ImmersiveStage(
                        state = state,
                        onPreviewHighlight = onPreviewHighlight,
                        onPreviewEndingChoice = onPreviewEndingChoice,
                        onChooseEndingBranch = onChooseEndingBranch,
                        onCollectHighlight = onCollectHighlight,
                        isLiked = state.likedEpisodes.any {
                            it.dramaTitle == drama?.title && it.episodeName == currentEpisode?.episodeName
                        },
                        isFavorited = drama?.title in state.favoritedDramaTitles,
                        onLike = onToggleLike,
                        onFavorite = onToggleFavorite,
                        onOpenBattle = {
                            battleExpanded.value = !battleExpanded.value
                            if (battleExpanded.value) {
                                collectionExpanded.value = false
                            }
                        },
                        onNextDrama = onNextDrama,
                        onPreviousDrama = onPreviousDrama,
                        onDismissOverlay = onDismissOverlay,
                        onToggleCollection = {
                            revealControls()
                            collectionExpanded.value = !collectionExpanded.value
                            if (collectionExpanded.value) {
                                battleExpanded.value = false
                            }
                        },
                        controlsVisible = controlsVisible.value || state.overlayState != OverlayState.None,
                        deferPlayback = showSplashScreen,
                        isFullscreen = isPlayerFullscreen,
                        onToggleFullscreen = {
                            revealControls()
                            collectionExpanded.value = false
                            battleExpanded.value = false
                            isEpisodePickerExpanded = false
                            isPlayerFullscreen = !isPlayerFullscreen
                        },
                        onPlaybackEnded = {
                            revealControls()
                            collectionExpanded.value = false
                            battleExpanded.value = false
                            isEpisodePickerExpanded = false
                            playNextEpisodeOrDrama()
                        },
                        onUserInteraction = { revealControls() },
                        onRegisterPreviewActions = { highlightAction, endingAction ->
                            previewHighlightAction = highlightAction
                            previewEndingAction = endingAction
                        },
                        modifier = if (isPlayerFullscreen) {
                            Modifier.fillMaxSize()
                        } else {
                            Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 10.dp)
                        }
                    )
                    if (!isPlayerFullscreen) {
                        Spacer(modifier = Modifier.height(playerBottomPadding))
                    }
                }

                AppTab.Discover -> DiscoverScreen(
                    onOpenDrama = { title ->
                        onSelectDrama(title)
                        activeTab = AppTab.Home
                        collectionExpanded.value = false
                    },
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(bottom = bottomContentPadding),
                )

                AppTab.Battle -> BattleArenaScreen(
                    state = state,
                    onCastVote = onCastVote,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(bottom = bottomContentPadding),
                )

                AppTab.Collection -> CollectionLibraryScreen(
                    state = state,
                    onCardClick = { selectedCollectionCard = it },
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(bottom = bottomContentPadding),
                )

                AppTab.Profile -> ProfileScreen(
                    state = state,
                    onUpdateProfileAvatar = onUpdateProfileAvatar,
                    onUpdateProfileName = onUpdateProfileName,
                    isLightTheme = isLightTheme,
                    onToggleTheme = { isLightTheme = !isLightTheme },
                    onOpenDrama = { title, episodeName ->
                        onOpenDramaEpisode(title, episodeName)
                        activeTab = AppTab.Home
                    },
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(bottom = bottomContentPadding),
                )
            }
        }

        if (activeTab == AppTab.Home &&
            !isPlayerFullscreen &&
            controlsVisible.value &&
            isEpisodePickerExpanded
        ) {
            EpisodePickerOverlay(
                episodes = drama?.episodes.orEmpty(),
                currentEpisode = currentEpisode,
                onCollapse = {
                    revealControls()
                    isEpisodePickerExpanded = false
                },
                onSelectEpisode = {
                    revealControls()
                    isEpisodePickerExpanded = false
                    onSelectEpisode(it)
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 78.dp, start = 12.dp, end = 12.dp),
            )
        }

        if (activeTab == AppTab.Home && !isPlayerFullscreen) {
            if (collectionExpanded.value) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color(0x66000000))
                        .clickable {
                            collectionExpanded.value = false
                        }
                ) {
                    BottomCollectionSheet(
                        state = state,
                        expanded = true,
                        onExpandedChange = {
                            collectionExpanded.value = it
                            if (it) battleExpanded.value = false
                        },
                        onCardClick = { selectedCollectionCard = it },
                        onPreviewHighlight = { previewHighlightAction?.invoke() },
                        onPreviewEndingChoice = { previewEndingAction?.invoke() },
                        bottomReservedPadding = bottomSheetContentPadding,
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth()
                            .padding(bottom = bottomSheetBottomGap)
                    )
                }
            }
            if (battleExpanded.value) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color(0x66000000))
                        .clickable {
                            battleExpanded.value = false
                        }
                ) {
                    BottomBattleSheet(
                        state = state,
                        expanded = true,
                        onExpandedChange = {
                            battleExpanded.value = it
                            if (it) collectionExpanded.value = false
                        },
                        onCastVote = onCastVote,
                        bottomReservedPadding = bottomSheetContentPadding,
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth()
                            .padding(bottom = bottomSheetBottomGap)
                    )
                }
            }
        }

        if (!isPlayerFullscreen) {
            BottomNavBar(
                selectedTab = activeTab,
                onSelectTab = {
                    activeTab = it
                    collectionExpanded.value = false
                    battleExpanded.value = false
                },
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .onGloballyPositioned {
                        measuredBottomNavHeight = with(density) { it.size.height.toDp() }
                    }
            )
        }

        selectedCollectionCard?.let { card ->
            CollectionCardDetailOverlay(
                card = card,
                onClose = { selectedCollectionCard = null },
                modifier = Modifier.fillMaxSize(),
            )
        }

        if (showSplashScreen) {
            AppSplashScreen(modifier = Modifier.fillMaxSize())
        }
    }
    }
}

@Composable
private fun EpisodePicker(
    episodes: List<EpisodeContent>,
    currentEpisode: EpisodeContent?,
    onToggleExpanded: () -> Unit,
    onSelectEpisode: (EpisodeContent) -> Unit,
) {
    val selectedIndex = episodes.indexOfFirst { it.episodeName == currentEpisode?.episodeName }
        .takeIf { it >= 0 } ?: 0
    val collapsedEpisodes = remember(episodes, selectedIndex) {
        val start = (selectedIndex - 1).coerceIn(0, (episodes.size - 4).coerceAtLeast(0))
        episodes.drop(start).take(4)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        collapsedEpisodes.forEach { episode ->
            EpisodePill(
                episode = episode,
                selected = episode.episodeName == currentEpisode?.episodeName,
                modifier = Modifier.weight(1f),
                onClick = { onSelectEpisode(episode) },
            )
        }
        repeat((4 - collapsedEpisodes.size).coerceAtLeast(0)) {
            Spacer(modifier = Modifier.weight(1f))
        }
        EpisodeTogglePill(
            label = "更多",
            onClick = onToggleExpanded,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun EpisodePickerOverlay(
    episodes: List<EpisodeContent>,
    currentEpisode: EpisodeContent?,
    onCollapse: () -> Unit,
    onSelectEpisode: (EpisodeContent) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalPlayerColors.current
    val isLight = colors == LightPlayerColors
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(22.dp),
        color = if (isLight) colors.surface else Color(0xD6081020),
        border = BorderStroke(1.dp, colors.border),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .height(156.dp)
                .verticalScroll(rememberScrollState())
                .padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            episodes.chunked(5).forEach { rowEpisodes ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    rowEpisodes.forEach { episode ->
                        EpisodePill(
                            episode = episode,
                            selected = episode.episodeName == currentEpisode?.episodeName,
                            modifier = Modifier.weight(1f),
                            onClick = { onSelectEpisode(episode) },
                        )
                    }
                    repeat(5 - rowEpisodes.size) {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
            }
            EpisodeTogglePill(
                label = "收起",
                onClick = onCollapse,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun EpisodePill(
    episode: EpisodeContent,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Surface(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(999.dp),
        color = if (selected) Color(0xFFD99000) else LocalPlayerColors.current.chip,
        border = BorderStroke(
            1.dp,
            if (selected) Color(0xFFD99000) else LocalPlayerColors.current.border,
        ),
    ) {
        Text(
            text = episode.episodeName,
            color = if (selected) Color(0xFF241600) else LocalPlayerColors.current.text,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 9.dp),
        )
    }
}

@Composable
private fun EpisodeTogglePill(
    label: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Surface(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(999.dp),
        color = LocalPlayerColors.current.chip,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Text(
            text = label,
            color = LocalPlayerColors.current.text,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 9.dp),
        )
    }
}

@Composable
private fun DiscoverScreen(
    onOpenDrama: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 14.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = "短剧",
            color = LocalPlayerColors.current.text,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = "选择短剧进入沉浸播放，收集高光卡与分支结局卡。",
            color = LocalPlayerColors.current.muted,
            style = MaterialTheme.typography.bodyMedium,
        )

        discoveryDramas.chunked(2).forEach { rowItems ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                rowItems.forEach { item ->
                    DramaDiscoveryCard(
                        item = item,
                        onClick = { onOpenDrama(item.title) },
                        modifier = Modifier.weight(1f),
                    )
                }
                if (rowItems.size == 1) {
                    Spacer(modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun BattleArenaScreen(
    state: PlayerUiState,
    onCastVote: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var guideExpanded by remember { mutableStateOf(false) }
    BattleArenaContent(
        state = state,
        onCastVote = onCastVote,
        modifier = modifier,
        header = {
            Surface(
                shape = RoundedCornerShape(22.dp),
                color = LocalPlayerColors.current.surface,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text(
                        text = "人气 PK",
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    Surface(
                        shape = RoundedCornerShape(18.dp),
                        color = LocalPlayerColors.current.surfaceRaised,
                        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { guideExpanded = !guideExpanded },
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    text = "玩法说明",
                                    color = LocalPlayerColors.current.text,
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    text = if (guideExpanded) "收起" else "展开",
                                    color = Color(0xFFD99000),
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.SemiBold,
                                )
                            }
                            if (!guideExpanded) {
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = "积分来源、投票消耗与 PK 规则",
                                    color = LocalPlayerColors.current.muted,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            if (guideExpanded) {
                                Spacer(modifier = Modifier.height(10.dp))
                                Column(
                                    verticalArrangement = Arrangement.spacedBy(6.dp),
                                ) {
                                    Text(
                                        text = "每收下一张高光卡或结局漫画卡，就自动获得 1 积分。你可以把积分投给喜欢的角色，或把怒火值砸向最招恨的角色。",
                                        color = LocalPlayerColors.current.muted,
                                        style = MaterialTheme.typography.bodyMedium,
                                    )
                                    Text(
                                        text = "1. 收下新高光卡 +1 分\n2. 收下新结局漫画卡 +1 分\n3. 进入 PK 页后，每投 1 票消耗 1 分",
                                        color = LocalPlayerColors.current.muted,
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                }
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        ProfileStatCard(
                            label = "可用积分",
                            value = state.availablePoints.toString(),
                            modifier = Modifier.weight(1f),
                        )
                        ProfileStatCard(
                            label = "人气值",
                            value = state.voteBoard.filter { it.track == VoteTrack.Support }.sumOf { it.votes }.toString(),
                            modifier = Modifier.weight(1f),
                        )
                        ProfileStatCard(
                            label = "怒火值",
                            value = state.voteBoard.filter { it.track == VoteTrack.Rage }.sumOf { it.votes }.toString(),
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        },
    )
}

@Composable
private fun BattleArenaContent(
    state: PlayerUiState,
    onCastVote: (String) -> Unit,
    modifier: Modifier = Modifier,
    header: @Composable (() -> Unit)? = null,
) {
    var selectedTrack by remember { mutableStateOf<VoteTrack?>(null) }
    val supportEntries = state.voteBoard.filter { it.track == VoteTrack.Support }
    val rageEntries = state.voteBoard.filter { it.track == VoteTrack.Rage }
    val supportTotal = supportEntries.sumOf { it.votes }
    val rageTotal = rageEntries.sumOf { it.votes }
    val supportLeader = supportEntries.maxByOrNull { it.votes } ?: supportEntries.first()
    val rageLeader = rageEntries.maxByOrNull { it.votes } ?: rageEntries.first()

    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        if (selectedTrack == null) {
            header?.invoke()

            Text(
                text = "本周榜位",
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                LeaderSpotlightCard(
                    label = "本周人气王",
                    entry = supportLeader,
                    accent = Color(0xFFD99000),
                    modifier = Modifier.fillMaxWidth(),
                )
                LeaderSpotlightCard(
                    label = "本周最招恨",
                    entry = rageLeader,
                    accent = Color(0xFFFF7A7A),
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            Text(
                text = "PK 专区",
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                VoteZoneEntryCard(
                    title = "人气值专区",
                    subtitle = "给你最想支持的角色投票",
                    entries = supportEntries,
                    totalVotes = supportTotal,
                    accent = Color(0xFFD99000),
                    onClick = { selectedTrack = VoteTrack.Support },
                    modifier = Modifier.fillMaxWidth(),
                )
                VoteZoneEntryCard(
                    title = "怒火值专区",
                    subtitle = "把不满投给最招恨的角色",
                    entries = rageEntries,
                    totalVotes = rageTotal,
                    accent = Color(0xFFFF7A7A),
                    onClick = { selectedTrack = VoteTrack.Rage },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        } else {
            val track = selectedTrack ?: VoteTrack.Support
            val isSupport = track == VoteTrack.Support
            VoteZoneDetailHeader(
                title = if (isSupport) "人气值专区" else "怒火值专区",
                subtitle = if (isSupport) "点赞越多，越说明观众站在他们这边。" else "每一票都记录对恶意和背叛的不满。",
                totalVotes = if (isSupport) supportTotal else rageTotal,
                accent = if (isSupport) Color(0xFFD99000) else Color(0xFFFF7A7A),
                onBack = { selectedTrack = null },
            )
            VoteColumn(
                title = if (isSupport) "角色列表" else "角色列表",
                subtitle = if (isSupport) "选择角色投 1 票，每次消耗 1 积分。" else "选择角色踩 1 票，每次消耗 1 积分。",
                entries = if (isSupport) supportEntries else rageEntries,
                accent = if (isSupport) Color(0xFFD99000) else Color(0xFFFF7A7A),
                buttonLabel = if (isSupport) "投 1 票" else "踩 1 票",
                availablePoints = state.availablePoints,
                onCastVote = onCastVote,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun VoteZoneEntryCard(
    title: String,
    subtitle: String,
    entries: List<VoteEntry>,
    totalVotes: Int,
    accent: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val leader = entries.maxByOrNull { it.votes }
    Surface(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(20.dp),
        color = LocalPlayerColors.current.surfaceAlt,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box {
                entries.take(3).forEachIndexed { index, entry ->
                    RemoteImage(
                        imageUrl = entry.thumbnailUrl,
                        contentDescription = entry.name,
                        modifier = Modifier
                            .padding(start = (index * 22).dp)
                            .size(54.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(LocalPlayerColors.current.chip),
                        contentScale = ContentScale.Crop,
                    )
                }
                if (entries.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .size(54.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(LocalPlayerColors.current.chip),
                    )
                }
            }
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Text(
                    text = title,
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = subtitle,
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = leader?.let { "当前领先：${it.name}" } ?: "暂无角色",
                    color = accent,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Column(
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Text(
                    text = "$totalVotes 票",
                    color = accent,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "进入 >",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun VoteZoneDetailHeader(
    title: String,
    subtitle: String,
    totalVotes: Int,
    accent: Color,
    onBack: () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "< 返回",
                    color = accent,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.clickable(onClick = onBack),
                )
                Text(
                    text = "$totalVotes 票",
                    color = accent,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                )
            }
            Text(
                text = title,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = subtitle,
                color = LocalPlayerColors.current.muted,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun LeaderSpotlightCard(
    label: String,
    entry: VoteEntry,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, accent.copy(alpha = 0.35f)),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = label,
                color = accent,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
            )
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RemoteImage(
                    imageUrl = entry.thumbnailUrl,
                    contentDescription = entry.name,
                    modifier = Modifier
                        .size(74.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(LocalPlayerColors.current.chip),
                    contentScale = ContentScale.Crop,
                )
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = entry.name,
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = entry.headline,
                        color = LocalPlayerColors.current.muted,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = "${entry.votes} 票",
                        color = accent,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun VoteColumn(
    title: String,
    subtitle: String,
    entries: List<VoteEntry>,
    accent: Color,
    buttonLabel: String,
    availablePoints: Int,
    onCastVote: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        color = LocalPlayerColors.current.surfaceAlt,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = title,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = subtitle,
                color = LocalPlayerColors.current.muted,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            entries.forEach { entry ->
                VoteEntryCard(
                    entry = entry,
                    accent = accent,
                    buttonLabel = buttonLabel,
                    canVote = availablePoints > 0,
                    onCastVote = { onCastVote(entry.key) },
                )
            }
        }
    }
}

@Composable
private fun VoteEntryCard(
    entry: VoteEntry,
    accent: Color,
    buttonLabel: String,
    canVote: Boolean,
    onCastVote: () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = LocalPlayerColors.current.surfaceRaised,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RemoteImage(
                    imageUrl = entry.thumbnailUrl,
                    contentDescription = entry.name,
                    modifier = Modifier
                        .size(72.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(LocalPlayerColors.current.chip),
                    contentScale = ContentScale.Crop,
                )
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        text = entry.headline,
                        color = accent,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = entry.name,
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = entry.description,
                        color = LocalPlayerColors.current.muted,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Surface(
                    shape = RoundedCornerShape(999.dp),
                    color = accent.copy(alpha = 0.15f),
                    border = BorderStroke(1.dp, accent.copy(alpha = 0.35f)),
                ) {
                    Text(
                        text = "${entry.votes} 票",
                        color = accent,
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    )
                }
                Text(
                    text = if (canVote) "每次消耗 1 积分" else "先去收集卡片赚积分",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.End,
                )
            }
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = canVote, onClick = onCastVote),
                shape = RoundedCornerShape(999.dp),
                color = if (canVote) accent else LocalPlayerColors.current.chip,
            ) {
                Box(
                    modifier = Modifier.padding(vertical = 11.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = if (canVote) buttonLabel else "积分不足",
                        color = if (canVote) Color(0xFF07111F) else Color(0x88FFFFFF),
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun DramaDiscoveryCard(
    item: DramaShelfItem,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = LocalPlayerColors.current.surfaceAlt,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(0.72f)
                    .clip(RoundedCornerShape(14.dp))
                    .background(
                        Brush.verticalGradient(
                            listOf(Color(0xFF23365F), Color(0xFF0A1020))
                        )
                    ),
                contentAlignment = Alignment.Center,
            ) {
                if (item.coverUrl.isNotBlank()) {
                    RemoteImage(
                        imageUrl = item.coverUrl,
                        contentDescription = item.title,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop,
                    )
                } else {
                    Text(
                        text = item.title.take(2),
                        color = Color(0xFFD99000),
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Text(
                text = item.title,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "${item.episodeCount} 集 · ${item.subtitle}",
                color = LocalPlayerColors.current.muted,
                style = MaterialTheme.typography.labelMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun CollectionLibraryScreen(
    state: PlayerUiState,
    onCardClick: (CollectionCard) -> Unit,
    modifier: Modifier = Modifier,
) {
    var selectedTab by remember { mutableStateOf(CollectionDetailTab.Home) }
    val currentDramaTitle = state.drama?.title
    val currentHighlightCards = remember(state.highlightCards, currentDramaTitle) {
        state.highlightCards.filter { it.dramaTitle == currentDramaTitle }
    }
    val currentEndingCards = remember(state.endingCards, currentDramaTitle) {
        state.endingCards.filter { it.dramaTitle == currentDramaTitle }
    }
    val highlightTotal = remember(state.drama) {
        state.drama?.episodes?.sumOf { it.highlights.size } ?: 0
    }
    val endingTotal = remember(state.drama) {
        state.drama?.episodes?.sumOf { it.endingChoice?.branches?.size ?: 0 } ?: 0
    }
    when (selectedTab) {
        CollectionDetailTab.Home -> {
            Column(
                modifier = modifier
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 14.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(
                    text = "看过的短剧",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "当前可用积分 ${state.availablePoints}，收下新高光卡或新结局漫画卡都会自动 +1。",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                )

                CollectionEntryCard(
                    title = "高光卡册",
                    subtitle = "身份揭晓、打脸反转、强情绪场面",
                    accent = Color(0xFFD99000),
                    count = currentHighlightCards.size,
                    totalCount = highlightTotal,
                    category = CardCategory.Highlight,
                    previewCard = currentHighlightCards.firstOrNull(),
                    onClick = { selectedTab = CollectionDetailTab.Highlight },
                )
                CollectionEntryCard(
                    title = "结局卡册",
                    subtitle = "分支漫画结局与不同走向沉淀在这里",
                    accent = Color(0xFF9B8BFF),
                    count = currentEndingCards.size,
                    totalCount = endingTotal,
                    category = CardCategory.Ending,
                    previewCard = currentEndingCards.firstOrNull(),
                    onClick = { selectedTab = CollectionDetailTab.Ending },
                )
            }
        }

        CollectionDetailTab.Highlight -> {
            CollectionDetailScreen(
                title = "高光卡册",
                subtitle = "已收集 ${currentHighlightCards.size}/$highlightTotal · 点击卡片查看大图与翻面效果",
                cards = currentHighlightCards,
                accent = Color(0xFFD99000),
                emptyText = "还没有收集到高光卡，先回到播放页触发一张。",
                onBack = { selectedTab = CollectionDetailTab.Home },
                onCardClick = onCardClick,
                modifier = modifier,
            )
        }

        CollectionDetailTab.Ending -> {
            CollectionDetailScreen(
                title = "结局卡册",
                subtitle = "已收集 ${currentEndingCards.size}/$endingTotal · 这里会收集每条分支生成的漫画结局卡",
                cards = currentEndingCards,
                accent = Color(0xFF9B8BFF),
                emptyText = "还没有收集到结局卡，先去剧情分支里拿一张。",
                onBack = { selectedTab = CollectionDetailTab.Home },
                onCardClick = onCardClick,
                modifier = modifier,
            )
        }
    }
}

@Composable
private fun CollectionEntryCard(
    title: String,
    subtitle: String,
    accent: Color,
    count: Int,
    totalCount: Int,
    category: CardCategory,
    previewCard: CollectionCard?,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .width(92.dp)
                    .aspectRatio(if ((previewCard?.category ?: category) == CardCategory.Ending) 0.94f else 0.74f)
                    .clip(RoundedCornerShape(14.dp))
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(
                                accent.copy(alpha = 0.65f),
                                Color(0xFF17233C),
                            )
                        )
                    ),
                contentAlignment = Alignment.Center,
            ) {
                if (previewCard != null) {
                    RemoteImage(
                        imageUrl = previewCard.imagePath,
                        contentDescription = previewCard.title,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop,
                    )
                } else {
                    CardBackImage(
                        category = category,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            }
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(
                    text = title,
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = subtitle,
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = "已收集 $count/$totalCount · 点击查看详情",
                    color = accent,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun CollectionDetailScreen(
    title: String,
    subtitle: String,
    cards: List<CollectionCard>,
    accent: Color,
    emptyText: String,
    onBack: () -> Unit,
    onCardClick: (CollectionCard) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 14.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Surface(
                modifier = Modifier.clickable(onClick = onBack),
                shape = CircleShape,
                color = LocalPlayerColors.current.border,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Box(
                    modifier = Modifier.size(36.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "‹",
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = title,
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = subtitle,
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        if (cards.isEmpty()) {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                color = Color(0x14000000),
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Text(
                    text = emptyText,
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(16.dp),
                )
            }
        } else {
            cards.forEach { card ->
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onCardClick(card) },
                    shape = RoundedCornerShape(20.dp),
                    color = LocalPlayerColors.current.surfaceAlt,
                    border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier
                                .width(110.dp)
                                .aspectRatio(if (card.category == CardCategory.Ending) 0.94f else 0.74f)
                                .clip(RoundedCornerShape(16.dp))
                                .background(
                                    Brush.verticalGradient(
                                        colors = if (card.category == CardCategory.Highlight) {
                                            listOf(Color(0xFFD99000), Color(0xFFFC8A4A))
                                        } else {
                                            listOf(Color(0xFFAA95FF), Color(0xFF4768FF))
                                        }
                                    )
                                ),
                        ) {
                            RemoteImage(
                                imageUrl = card.imagePath,
                                contentDescription = card.title,
                                modifier = Modifier.fillMaxSize(),
                                contentScale = ContentScale.Crop,
                            )
                        }
                        Column(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(6.dp),
                        ) {
                            Text(
                                text = card.title,
                                color = LocalPlayerColors.current.text,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                text = card.description,
                                color = LocalPlayerColors.current.muted,
                                style = MaterialTheme.typography.bodyMedium,
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                text = card.episodeName,
                                color = accent,
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ProfileScreen(
    state: PlayerUiState,
    onUpdateProfileAvatar: (String?) -> Unit,
    onUpdateProfileName: (String) -> Unit,
    isLightTheme: Boolean,
    onToggleTheme: () -> Unit,
    onOpenDrama: (String, String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val colors = LocalPlayerColors.current
    var selectedTab by remember { mutableStateOf(ProfileDetailTab.Home) }
    var showNameEditor by remember { mutableStateOf(false) }
    var pendingName by remember(state.profileName) { mutableStateOf(state.profileName) }
    val avatarPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            runCatching {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            }
            onUpdateProfileAvatar(uri.toString())
        }
    }
    val latestLikedByDrama = state.likedEpisodes
        .groupBy { it.dramaTitle }
        .mapValues { (_, entries) -> entries.first() }
        .values
        .toList()
    val latestHistoryByDrama = state.watchHistory
        .groupBy { it.dramaTitle }
        .mapValues { (_, entries) -> entries.first() }
        .values
        .toList()
    val avatarPalette = remember {
        listOf(
            Color(0xFFE8EEF9) to Color(0xFF25304A),
            Color(0xFFD99000) to Color(0xFF3D2B00),
            Color(0xFFB8E4FF) to Color(0xFF18334E),
            Color(0xFFFFC8D8) to Color(0xFF4A2031),
            Color(0xFFC6F5D0) to Color(0xFF173525),
        )
    }
    val avatarText = remember {
        listOf("剧", "追", "映", "卡", "赏")
    }
    val avatarIndex = state.profileAvatarIndex.mod(avatarPalette.size)
    val (avatarBg, avatarFg) = avatarPalette[avatarIndex]

    if (showNameEditor) {
        AlertDialog(
            onDismissRequest = { showNameEditor = false },
            title = {
                Text(
                    text = "修改昵称",
                    color = LocalPlayerColors.current.text,
                    fontWeight = FontWeight.Bold,
                )
            },
            text = {
                OutlinedTextField(
                    value = pendingName,
                    onValueChange = { pendingName = it.take(12) },
                    singleLine = true,
                    label = { Text("昵称") },
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        onUpdateProfileName(pendingName)
                        showNameEditor = false
                    }
                ) {
                    Text("保存", color = Color(0xFFD99000))
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        pendingName = state.profileName
                        showNameEditor = false
                    }
                ) {
                    Text("取消", color = LocalPlayerColors.current.muted)
                }
            },
            containerColor = LocalPlayerColors.current.surface,
        )
    }

    when (selectedTab) {
        ProfileDetailTab.Home -> {
            Column(
                modifier = modifier
                    .verticalScroll(rememberScrollState())
                    .navigationBarsPadding()
                    .padding(horizontal = 18.dp, vertical = 24.dp)
                    .padding(bottom = 104.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Surface(
                        modifier = Modifier.clickable {
                            avatarPickerLauncher.launch(arrayOf("image/*"))
                        },
                        shape = CircleShape,
                        color = avatarBg,
                        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                    ) {
                        Box(
                            modifier = Modifier.size(58.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            if (state.profileAvatarUri != null) {
                                RemoteImage(
                                    imageUrl = state.profileAvatarUri,
                                    contentDescription = "头像",
                                    modifier = Modifier.fillMaxSize(),
                                )
                            } else {
                                Text(
                                    avatarText[avatarIndex],
                                    color = avatarFg,
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold,
                                )
                            }
                        }
                    }
                    Column(
                        modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(3.dp),
                    ) {
                        Text(
                            text = state.profileName,
                            color = colors.text,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.clickable {
                                pendingName = state.profileName
                                showNameEditor = true
                            },
                        )
                        Text(
                            text = "互动短剧账号",
                            color = colors.muted,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                    ThemeToggleButton(
                        isLightTheme = isLightTheme,
                        onToggleTheme = onToggleTheme,
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ProfileStatCard(
                        label = "点赞",
                        value = state.likedEpisodes.size.toString(),
                        modifier = Modifier.weight(1f),
                    )
                    ProfileStatCard(
                        label = "收藏",
                        value = state.favoritedDramaTitles.size.toString(),
                        modifier = Modifier.weight(1f),
                    )
                    ProfileStatCard(
                        label = "历史",
                        value = latestHistoryByDrama.size.toString(),
                        modifier = Modifier.weight(1f),
                    )
                }

                CacheManagementCard(
                    cacheCount = ImageMemoryCache.count,
                    cacheBytes = ImageMemoryCache.totalBytes,
                    onClearCache = { ImageMemoryCache.clear() },
                )

                Text(
                    text = "内容资产",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "已收录剧集视频、封面、高光卡和分支结局漫画。",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                )

                Text(
                    text = "我的点赞",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                DramaEntryList(
                    entries = latestLikedByDrama,
                    emptyText = "还没有点赞的剧集。",
                    onOpenDrama = onOpenDrama,
                )

                Text(
                    text = "我的收藏",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                DramaTitleList(
                    titles = state.favoritedDramaTitles.toList(),
                    emptyText = "还没有收藏的短剧。",
                    onOpenDrama = onOpenDrama,
                )

                Text(
                    text = "最近收藏",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = when {
                        state.highlightCards.isEmpty() && state.endingCards.isEmpty() ->
                            "还没有收藏内容，先在播放页收下一张高光卡或结局卡。"
                        else ->
                            (state.highlightCards + state.endingCards)
                                .takeLast(3)
                                .reversed()
                                .joinToString("\n") { "· ${it.episodeName} · ${it.title}" }
                    },
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "历史记录",
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    if (latestHistoryByDrama.size > 5) {
                        Text(
                            text = "查看全部",
                            color = Color(0xFFD99000),
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.clickable { selectedTab = ProfileDetailTab.History },
                        )
                    }
                }
                HistoryEntryList(
                    entries = latestHistoryByDrama.take(5),
                    emptyText = "还没有观看记录。",
                    onOpenDrama = onOpenDrama,
                )
            }
        }

        ProfileDetailTab.History -> {
            HistoryDetailScreen(
                entries = latestHistoryByDrama,
                onBack = { selectedTab = ProfileDetailTab.Home },
                onOpenDrama = onOpenDrama,
                modifier = modifier,
            )
        }
    }
}

@Composable
private fun DramaTitleList(
    titles: List<String>,
    emptyText: String,
    onOpenDrama: (String, String?) -> Unit,
) {
    if (titles.isEmpty()) {
        Text(
            text = emptyText,
            color = LocalPlayerColors.current.muted,
            style = MaterialTheme.typography.bodyMedium,
        )
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        titles.forEach { title ->
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpenDrama(title, null) },
                shape = RoundedCornerShape(16.dp),
                color = LocalPlayerColors.current.surface,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = title,
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "查看",
                        color = Color(0xFFD99000),
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

@Composable
private fun DramaEntryList(
    entries: List<WatchHistoryEntry>,
    emptyText: String,
    onOpenDrama: (String, String?) -> Unit,
) {
    if (entries.isEmpty()) {
        Text(
            text = emptyText,
            color = LocalPlayerColors.current.muted,
            style = MaterialTheme.typography.bodyMedium,
        )
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        entries.forEach { entry ->
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpenDrama(entry.dramaTitle, entry.episodeName) },
                shape = RoundedCornerShape(16.dp),
                color = LocalPlayerColors.current.surface,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            text = entry.dramaTitle,
                            color = LocalPlayerColors.current.text,
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "最近点赞：${entry.episodeName}",
                            color = LocalPlayerColors.current.muted,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    Text(
                        text = "查看",
                        color = Color(0xFFD99000),
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

@Composable
private fun HistoryEntryList(
    entries: List<WatchHistoryEntry>,
    emptyText: String,
    onOpenDrama: (String, String?) -> Unit,
) {
    if (entries.isEmpty()) {
        Text(
            text = emptyText,
            color = LocalPlayerColors.current.muted,
            style = MaterialTheme.typography.bodyMedium,
        )
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        entries.forEach { entry ->
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpenDrama(entry.dramaTitle, entry.episodeName) },
                shape = RoundedCornerShape(16.dp),
                color = LocalPlayerColors.current.surface,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            text = entry.dramaTitle,
                            color = LocalPlayerColors.current.text,
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = entry.episodeName,
                            color = LocalPlayerColors.current.muted,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun HistoryDetailScreen(
    entries: List<WatchHistoryEntry>,
    onBack: () -> Unit,
    onOpenDrama: (String, String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .navigationBarsPadding()
            .padding(horizontal = 18.dp, vertical = 24.dp)
            .padding(bottom = 104.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Surface(
                modifier = Modifier.clickable(onClick = onBack),
                shape = CircleShape,
                color = LocalPlayerColors.current.border,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Box(
                    modifier = Modifier.size(36.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "‹",
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = "全部历史记录",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "点击任意记录回到对应剧集",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        HistoryEntryList(
            entries = entries,
            emptyText = "还没有观看记录。",
            onOpenDrama = onOpenDrama,
        )
    }
}

@Composable
private fun ThemeToggleButton(
    isLightTheme: Boolean,
    onToggleTheme: () -> Unit,
) {
    val colors = LocalPlayerColors.current
    Surface(
        modifier = Modifier.clickable(onClick = onToggleTheme),
        shape = RoundedCornerShape(999.dp),
        color = colors.surfaceAlt,
        border = BorderStroke(1.dp, colors.border),
    ) {
        Row(
            modifier = Modifier.padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            ThemeModeIcon(label = "☀", selected = isLightTheme)
            ThemeModeIcon(label = "☾", selected = !isLightTheme)
        }
    }
}

@Composable
private fun ThemeModeIcon(
    label: String,
    selected: Boolean,
) {
    val colors = LocalPlayerColors.current
    Surface(
        shape = CircleShape,
        color = if (selected) colors.navSelected else Color.Transparent,
    ) {
        Box(
            modifier = Modifier.size(30.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = label,
                color = if (selected) Color(0xFFC97900) else colors.muted,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun ProfileStatCard(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = value,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = label,
                color = LocalPlayerColors.current.muted,
                style = MaterialTheme.typography.labelMedium,
            )
        }
    }
}

@Composable
private fun CacheManagementCard(
    cacheCount: Int,
    cacheBytes: Int,
    onClearCache: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "当前缓存 ${formatCacheSize(cacheBytes)}",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "$cacheCount 张图片",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Surface(
                modifier = Modifier.clickable(
                    enabled = cacheCount > 0,
                    onClick = onClearCache,
                ),
                shape = RoundedCornerShape(999.dp),
                color = if (cacheCount > 0) Color(0xFFD99000) else LocalPlayerColors.current.chip,
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Text(
                    text = "清除缓存",
                    color = if (cacheCount > 0) Color(0xFF07111F) else LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
                )
            }
        }
    }
}

private fun formatCacheSize(bytes: Int): String {
    val kb = bytes / 1024.0
    if (kb < 1024.0) {
        return "${kb.roundToLong()} KB"
    }
    val mb = kb / 1024.0
    return "${(mb * 10).roundToLong() / 10.0} MB"
}

@Composable
private fun ImmersiveStage(
    state: PlayerUiState,
    onPreviewHighlight: (String) -> Unit,
    onPreviewEndingChoice: () -> Unit,
    onChooseEndingBranch: (EndingBranch) -> Unit,
    onCollectHighlight: (CollectionCard) -> Unit,
    isLiked: Boolean,
    isFavorited: Boolean,
    onLike: () -> Unit,
    onFavorite: () -> Unit,
    onOpenBattle: () -> Unit,
    onNextDrama: () -> Unit,
    onPreviousDrama: () -> Unit,
    onDismissOverlay: () -> Unit,
    onToggleCollection: () -> Unit,
    controlsVisible: Boolean,
    deferPlayback: Boolean,
    isFullscreen: Boolean,
    onToggleFullscreen: () -> Unit,
    onPlaybackEnded: () -> Unit,
    onUserInteraction: () -> Unit,
    onRegisterPreviewActions: ((() -> Unit)?, (() -> Unit)?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val episode = state.currentEpisode
    val episodeKey = episode?.videoPath
    val context = LocalContext.current
    val player = remember(context) {
        ExoPlayer.Builder(context).build().apply {
            repeatMode = Player.REPEAT_MODE_OFF
            playWhenReady = true
        }
    }
    val endingShown = remember(episodeKey) { mutableStateOf(false) }
    val triggeredHighlightIds = remember(episodeKey) { mutableStateOf(emptySet<String>()) }
    val preferredTrigger = remember(episodeKey) { mutableStateOf<String?>(null) }
    val suppressAutoHighlights = remember(episodeKey) { mutableStateOf(false) }
    val suppressAutoEnding = remember(episodeKey) { mutableStateOf(false) }
    val isPlaying = remember { mutableStateOf(true) }
    val durationMs = remember { mutableLongStateOf(1L) }
    val positionMs = remember { mutableLongStateOf(0L) }
    val sliderValue = remember { mutableFloatStateOf(0f) }
    val isSeeking = remember { mutableStateOf(false) }
    val hasAutoAdvanced = remember(episodeKey) { mutableStateOf(false) }
    val swipeThresholdPx = with(LocalDensity.current) { 72.dp.toPx() }
    val dramaSwipeDistance = remember { mutableFloatStateOf(0f) }
    val dramaSwipeModifier = Modifier.draggable(
        orientation = Orientation.Vertical,
        state = rememberDraggableState { delta ->
            dramaSwipeDistance.floatValue += delta
        },
        onDragStopped = {
            when {
                dramaSwipeDistance.floatValue > swipeThresholdPx -> onNextDrama()
                dramaSwipeDistance.floatValue < -swipeThresholdPx -> onPreviousDrama()
            }
            dramaSwipeDistance.floatValue = 0f
        },
    )

    fun syncTriggerWindowsForPosition(targetMs: Long) {
        val targetSec = targetMs.coerceAtLeast(0L) / 1000.0
        val allHighlights = episode?.highlights.orEmpty()
        triggeredHighlightIds.value = allHighlights
            .filter { highlight -> targetSec >= (highlight.pauseAtSec ?: highlight.triggerAtSec) }
            .map { it.id }
            .toSet()
        val endingTrigger = episode?.endingChoice?.let { it.pauseAtSec ?: it.triggerAtSec }
        endingShown.value = endingTrigger?.let { targetSec >= it } ?: false
        preferredTrigger.value = null
        suppressAutoHighlights.value = false
        suppressAutoEnding.value = false
    }

    DisposableEffect(player) {
        onDispose {
            player.release()
        }
    }

    DisposableEffect(player, episodeKey) {
        val listener = object : Player.Listener {
            override fun onIsPlayingChanged(playing: Boolean) {
                isPlaying.value = playing
            }

            override fun onPlaybackStateChanged(playbackState: Int) {
                durationMs.longValue = player.duration.takeIf { it > 0 } ?: 1L
                if (playbackState == Player.STATE_ENDED && !hasAutoAdvanced.value) {
                    hasAutoAdvanced.value = true
                    onPlaybackEnded()
                }
            }
        }
        player.addListener(listener)
        onDispose {
            player.removeListener(listener)
        }
    }

    LaunchedEffect(episodeKey) {
        endingShown.value = false
        triggeredHighlightIds.value = emptySet()
        preferredTrigger.value = null
        suppressAutoHighlights.value = false
        suppressAutoEnding.value = false
        positionMs.longValue = 0L
        sliderValue.floatValue = 0f
        val path = episode?.videoPath
        if (path != null) {
            player.setMediaItem(MediaItem.fromUri(Uri.parse(path)))
            player.playWhenReady = !deferPlayback
            player.prepare()
            player.seekTo(0)
            if (deferPlayback) {
                player.pause()
            } else {
                player.play()
            }
        }
    }

    LaunchedEffect(deferPlayback, episodeKey) {
        if (!deferPlayback && episode?.videoPath != null) {
            player.playWhenReady = true
            player.play()
        }
    }

    LaunchedEffect(episodeKey) {
        val highlightAction = episode?.highlights?.firstOrNull()?.let { highlight ->
            {
                triggeredHighlightIds.value = triggeredHighlightIds.value - highlight.id
                endingShown.value = true
                preferredTrigger.value = "highlight"
                suppressAutoHighlights.value = false
                suppressAutoEnding.value = true
                val startSec = highlight.startAtSec ?: (highlight.triggerAtSec - 5.0)
                player.seekTo((startSec.coerceAtLeast(0.0) * 1000).roundToLong())
                player.play()
            }
        }
        val endingAction = episode?.endingChoice?.let { endingChoice ->
            {
                triggeredHighlightIds.value = episode.highlights.map { it.id }.toSet()
                endingShown.value = false
                preferredTrigger.value = "ending"
                suppressAutoHighlights.value = true
                suppressAutoEnding.value = false
                val startSec = endingChoice.startAtSec ?: (endingChoice.triggerAtSec - 12.0)
                player.seekTo((startSec.coerceAtLeast(0.0) * 1000).roundToLong())
                player.play()
            }
        }
        onRegisterPreviewActions(highlightAction, endingAction)
    }

    LaunchedEffect(player, episodeKey, state.overlayState) {
        while (true) {
            val duration = player.duration.takeIf { it > 0 } ?: 1L
            durationMs.longValue = duration
            if (!isSeeking.value) {
                val currentPos = player.currentPosition.coerceAtLeast(0L)
                positionMs.longValue = currentPos
                sliderValue.floatValue = (currentPos.toFloat() / duration.toFloat()).coerceIn(0f, 1f)
            }

            val currentEpisode = episode
            if (currentEpisode != null && state.overlayState == OverlayState.None && player.isPlaying) {
                val currentSec = player.currentPosition / 1000.0
                val dueHighlight = currentEpisode.highlights.firstOrNull { highlight ->
                    highlight.id !in triggeredHighlightIds.value &&
                        currentSec >= (highlight.pauseAtSec ?: highlight.triggerAtSec)
                }
                val endingTrigger = currentEpisode.endingChoice?.let { choice ->
                    choice.pauseAtSec ?: choice.triggerAtSec
                }
                val endingDue = !endingShown.value && endingTrigger != null && currentSec >= endingTrigger
                if (dueHighlight != null && preferredTrigger.value != "ending" && !suppressAutoHighlights.value) {
                    triggeredHighlightIds.value = triggeredHighlightIds.value + dueHighlight.id
                    preferredTrigger.value = null
                    player.pause()
                    onPreviewHighlight(dueHighlight.id)
                } else if (endingDue && preferredTrigger.value != "highlight" && !suppressAutoEnding.value) {
                    endingShown.value = true
                    preferredTrigger.value = null
                    player.pause()
                    onPreviewEndingChoice()
                }
            }
            delay(200)
        }
    }

    LaunchedEffect(state.overlayState) {
        if (state.overlayState != OverlayState.None) {
            player.pause()
        }
    }

    Card(
        modifier = modifier.then(dramaSwipeModifier),
        shape = if (isFullscreen) RoundedCornerShape(0.dp) else RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0D16)),
        border = if (isFullscreen) null else BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Box(
            modifier = (if (isFullscreen) Modifier.fillMaxSize() else Modifier
                .fillMaxWidth()
                .aspectRatio(9f / 16f))
                .background(Color.Black)
                .clickable {
                    onUserInteraction()
                    if (controlsVisible) {
                        if (player.isPlaying) player.pause() else player.play()
                    }
                }
        ) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { viewContext ->
                    PlayerView(viewContext).apply {
                        useController = false
                        this.player = player
                        setShutterBackgroundColor(android.graphics.Color.TRANSPARENT)
                    }
                },
                update = { playerView ->
                    playerView.player = player
                },
            )

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(
                                Color.Transparent,
                                Color.Transparent,
                                Color(0xCC02040A),
                            )
                        )
                    )
            )

            if (controlsVisible) {
                Column(
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = episode?.episodeName ?: "未选择剧集",
                        color = Color.White,
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
                if (isFullscreen) {
                    Surface(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .statusBarsPadding()
                            .padding(top = 12.dp, end = 16.dp)
                            .clickable {
                                onUserInteraction()
                                onToggleFullscreen()
                            },
                        shape = CircleShape,
                        color = Color(0x66000000),
                        border = BorderStroke(1.dp, Color(0x30FFFFFF)),
                    ) {
                        Box(
                            modifier = Modifier.size(42.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                text = "⤢",
                                color = Color.White,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    }
                }
            }

            if (!isPlaying.value && controlsVisible) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.Center)
                        .size(84.dp),
                    shape = CircleShape,
                    color = Color(0x66000000),
                    border = BorderStroke(1.dp, Color(0x30FFFFFF)),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .clickable { player.play() },
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = "▶",
                            color = Color.White,
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }

            ActionRail(
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .padding(end = 10.dp),
                visible = controlsVisible,
                isLiked = isLiked,
                isFavorited = isFavorited,
                onLike = {
                    onUserInteraction()
                    onLike()
                },
                onFavorite = {
                    onUserInteraction()
                    onFavorite()
                },
                onOpenBattle = {
                    onUserInteraction()
                    onOpenBattle()
                },
                onToggleCollection = {
                    onUserInteraction()
                    onToggleCollection()
                },
            )

            val hasOverlay = state.overlayState != OverlayState.None
            val isFullCardOverlay = state.overlayState is OverlayState.Highlight ||
                state.overlayState is OverlayState.EndingResult
            if (controlsVisible) {
                PlaybackControls(
                    isPlaying = isPlaying.value,
                    progress = sliderValue.floatValue,
                    currentMs = positionMs.longValue,
                    durationMs = durationMs.longValue,
                    onTogglePlay = {
                        onUserInteraction()
                        if (player.isPlaying) player.pause() else player.play()
                    },
                    onSeekChange = { value ->
                        onUserInteraction()
                        isSeeking.value = true
                        sliderValue.floatValue = value
                    },
                    onSeekFinished = {
                        onUserInteraction()
                        val target = (durationMs.longValue * sliderValue.floatValue).roundToLong()
                        player.seekTo(target)
                        positionMs.longValue = target
                        isSeeking.value = false
                        syncTriggerWindowsForPosition(target)
                    },
                    isFullscreen = isFullscreen,
                    onToggleFullscreen = {
                        onUserInteraction()
                        onToggleFullscreen()
                    },
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .fillMaxWidth()
                        .padding(
                            start = 18.dp,
                            end = 18.dp,
                            bottom = if (hasOverlay && !isFullCardOverlay) 150.dp else 16.dp,
                        ),
                )

                Column(
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .fillMaxWidth()
                        .padding(
                            start = 16.dp,
                            end = 72.dp,
                            bottom = if (hasOverlay && !isFullCardOverlay) 208.dp else 90.dp,
                        ),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    val subCaption = dramaSubCaption(state)
                    Text(
                        text = dramaCaption(state),
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (subCaption.isNotBlank()) {
                        Text(
                            text = subCaption,
                            color = Color(0xFFCAD4EA),
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 3,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }

            when (val overlay = state.overlayState) {
                is OverlayState.Highlight -> {
                    CollectionCardDetailOverlay(
                        card = overlay.card,
                        initiallyShowingBack = true,
                        actionLabel = "收下并继续播放",
                        onAction = {
                            onCollectHighlight(overlay.card)
                            onDismissOverlay()
                            player.play()
                        },
                        onClose = {
                            onDismissOverlay()
                            player.play()
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                }

                is OverlayState.EndingResult -> {
                    CollectionCardDetailOverlay(
                        card = overlay.card,
                        initiallyShowingBack = true,
                        actionLabel = "继续播放",
                        onAction = {
                            onDismissOverlay()
                            player.play()
                        },
                        onClose = {
                            onDismissOverlay()
                            player.play()
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                }

                else -> Unit
            }

            if (hasOverlay && !isFullCardOverlay) {
                val overlaySheetColor = if (LocalPlayerColors.current == LightPlayerColors) {
                    LocalPlayerColors.current.surface
                } else {
                    Color(0xE8131B2D)
                }
                Surface(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth(),
                    shape = RoundedCornerShape(topStart = 26.dp, topEnd = 26.dp),
                    color = overlaySheetColor,
                    border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                ) {
                    OverlaySurface(
                        state = state,
                        onChooseEndingBranch = onChooseEndingBranch,
                        onCollectHighlight = onCollectHighlight,
                        onDismissOverlay = onDismissOverlay,
                        onResumePlayback = { player.play() },
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun PlaybackControls(
    isPlaying: Boolean,
    progress: Float,
    currentMs: Long,
    durationMs: Long,
    onTogglePlay: () -> Unit,
    onSeekChange: (Float) -> Unit,
    onSeekFinished: () -> Unit,
    isFullscreen: Boolean,
    onToggleFullscreen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Slider(
            value = progress,
            onValueChange = onSeekChange,
            onValueChangeFinished = onSeekFinished,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Surface(
                shape = CircleShape,
                color = Color(0x66000000),
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                modifier = Modifier
                    .size(40.dp)
                    .clickable(onClick = onTogglePlay),
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = if (isPlaying) "❚❚" else "▶",
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Text(
                text = "${formatMs(currentMs)} / ${formatMs(durationMs)}",
                color = Color.White,
                style = MaterialTheme.typography.labelMedium,
            )
            Spacer(modifier = Modifier.weight(1f))
            if (!isFullscreen) {
                Surface(
                    shape = CircleShape,
                    color = Color(0x66000000),
                    border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                    modifier = Modifier
                        .size(40.dp)
                        .clickable(onClick = onToggleFullscreen),
                ) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = "⛶",
                            color = Color.White,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ActionRail(
    modifier: Modifier = Modifier,
    visible: Boolean,
    isLiked: Boolean,
    isFavorited: Boolean,
    onLike: () -> Unit,
    onFavorite: () -> Unit,
    onOpenBattle: () -> Unit,
    onToggleCollection: () -> Unit,
) {
    if (!visible) return

    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        RailButton(symbol = "👍", label = "点赞", selected = isLiked, onClick = onLike)
        RailButton(symbol = "★", label = "收藏", selected = isFavorited, onClick = onFavorite)
        RailButton(symbol = "PK", label = "投票", onClick = onOpenBattle)
        RailButton(symbol = "册", label = "卡册", onClick = onToggleCollection)
    }
}

@Composable
private fun RailButton(
    symbol: String,
    label: String,
    selected: Boolean = false,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier.clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Surface(
            shape = CircleShape,
            color = if (selected) Color(0x33D99000) else Color(0x26000000),
            border = BorderStroke(1.dp, if (selected) Color(0x88D99000) else LocalPlayerColors.current.border),
        ) {
            Box(
                modifier = Modifier.size(48.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = symbol,
                    color = if (selected) Color(0xFFD99000) else Color.White,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
        Text(
            text = label,
            color = if (selected) Color(0xFFD99000) else Color.White,
            style = MaterialTheme.typography.labelSmall,
        )
    }
}

@Composable
private fun OverlaySurface(
    state: PlayerUiState,
    onChooseEndingBranch: (EndingBranch) -> Unit,
    onCollectHighlight: (CollectionCard) -> Unit,
    onDismissOverlay: () -> Unit,
    onResumePlayback: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when (val overlay = state.overlayState) {
        OverlayState.None -> {
            Column(
                modifier = modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    text = "互动节点",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "剧情会在高光点与结局分支点给出互动提示。",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.bodyMedium,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    StatusPill(label = "Overlay", value = "None")
                    StatusPill(label = "高光", value = "${state.currentEpisode?.highlights?.size ?: 0}")
                    StatusPill(label = "分支", value = "${state.currentEpisode?.endingChoice?.branches?.size ?: 0}")
                }
            }
        }

        is OverlayState.Highlight -> OverlayCard(
            title = overlay.card.title,
            description = overlay.card.description,
            imagePath = overlay.card.imagePath,
            accent = Color(0xFFD99000),
            actionLabel = "收下并继续播放",
            onAction = {
                onCollectHighlight(overlay.card)
                onDismissOverlay()
                onResumePlayback()
            },
            modifier = modifier,
        )

        is OverlayState.EndingResult -> OverlayCard(
            title = overlay.card.title,
            description = overlay.card.description,
            imagePath = overlay.card.imagePath,
            accent = Color(0xFF9E88FF),
            actionLabel = "继续播放",
            onAction = {
                onDismissOverlay()
                onResumePlayback()
            },
            modifier = modifier,
        )

        is OverlayState.EndingChoice -> {
            val branches = overlay.episode.endingChoice?.branches.orEmpty()
            Column(
                modifier = modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text(
                    text = overlay.episode.endingChoice?.question ?: "做出你的选择",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                branches.forEach { branch ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onChooseEndingBranch(branch) },
                        shape = RoundedCornerShape(18.dp),
                        color = LocalPlayerColors.current.surfaceAlt,
                        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                    ) {
                        Column(
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                            verticalArrangement = Arrangement.spacedBy(4.dp),
                        ) {
                            Text(
                                text = branch.optionLabel,
                                color = LocalPlayerColors.current.text,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.SemiBold,
                            )
                            Text(
                                text = "选择后解锁：${branch.cardTitle}",
                                color = LocalPlayerColors.current.muted,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusPill(label: String, value: String) {
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = Color(0x14000000),
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Text(
            text = "$label  $value",
            color = LocalPlayerColors.current.text,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
        )
    }
}

@Composable
private fun OverlayCard(
    title: String,
    description: String,
    imagePath: String,
    accent: Color,
    actionLabel: String,
    onAction: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        RemoteImage(
            imageUrl = imagePath,
            contentDescription = title,
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(LocalPlayerColors.current.chip),
            contentScale = ContentScale.Crop,
        )
        Text(
            text = title,
            color = accent,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        if (description.isNotBlank()) {
            Text(
                text = description,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Button(onClick = onAction) {
            Text(actionLabel)
        }
    }
}

@Composable
private fun BottomCollectionSheet(
    state: PlayerUiState,
    expanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    onCardClick: (CollectionCard) -> Unit,
    onPreviewHighlight: () -> Unit,
    onPreviewEndingChoice: () -> Unit,
    bottomReservedPadding: Dp,
    modifier: Modifier = Modifier,
) {
    if (!expanded) return

    val density = LocalDensity.current
    val dragThresholdPx = with(density) { 36.dp.toPx() }
    val dragDistance = remember { mutableFloatStateOf(0f) }
    val sheetDragState = rememberDraggableState { delta ->
        dragDistance.floatValue += delta
    }
    val sheetDragModifier = Modifier.draggable(
        orientation = Orientation.Vertical,
        state = sheetDragState,
        onDragStopped = {
            when {
                dragDistance.floatValue > dragThresholdPx -> onExpandedChange(false)
                dragDistance.floatValue < -dragThresholdPx -> onExpandedChange(true)
            }
            dragDistance.floatValue = 0f
        },
    )

    Surface(
        modifier = modifier
            .height(420.dp)
            .then(sheetDragModifier),
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        color = LocalPlayerColors.current.nav,
        tonalElevation = 0.dp,
        shadowElevation = 0.dp,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp, bottom = bottomReservedPadding),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .width(44.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(Color(0x44172033))
                    .then(sheetDragModifier)
                    .clickable { onExpandedChange(!expanded) }
            )

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .then(sheetDragModifier)
                    .clickable { onExpandedChange(!expanded) }
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "卡册",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "下拉收起",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.labelMedium,
                )
            }

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = "高光卡负责情绪爆点，结局卡负责分支结局，整体更像短视频里的互动收藏。",
                        color = Color(0xFF93A5C8),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }

                val hasHighlight = state.currentEpisode?.highlights?.isNotEmpty() == true
                val hasEnding = state.currentEpisode?.endingChoice != null
                if (hasHighlight || hasEnding) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        if (hasHighlight) {
                            Surface(
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable(onClick = onPreviewHighlight),
                                shape = RoundedCornerShape(999.dp),
                                color = LocalPlayerColors.current.chip,
                                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                            ) {
                                Text(
                                    text = "定位高光",
                                    color = LocalPlayerColors.current.text,
                                    style = MaterialTheme.typography.labelLarge,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
                                    textAlign = TextAlign.Center,
                                )
                            }
                        }
                        if (hasEnding) {
                            Surface(
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable(onClick = onPreviewEndingChoice),
                                shape = RoundedCornerShape(999.dp),
                                color = LocalPlayerColors.current.chip,
                                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                            ) {
                                Text(
                                    text = "剧情选择",
                                    color = LocalPlayerColors.current.text,
                                    style = MaterialTheme.typography.labelLarge,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
                                    textAlign = TextAlign.Center,
                                )
                            }
                        }
                    }
                }

                CollectionPreviewRow(
                    title = "高光卡册",
                    subtitle = "身份揭晓、打脸反转、强情绪场面",
                    cards = state.highlightCards.filter { it.dramaTitle == state.drama?.title },
                    category = CardCategory.Highlight,
                    accent = Color(0xFFD99000),
                    totalCount = state.drama?.episodes?.sumOf { it.highlights.size } ?: 0,
                    onCardClick = onCardClick,
                )
                CollectionPreviewRow(
                    title = "结局卡册",
                    subtitle = "每条分支都落一张漫画结局卡",
                    cards = state.endingCards.filter { it.dramaTitle == state.drama?.title },
                    category = CardCategory.Ending,
                    accent = Color(0xFF9B8BFF),
                    totalCount = state.drama?.episodes?.sumOf { it.endingChoice?.branches?.size ?: 0 } ?: 0,
                    onCardClick = onCardClick,
                )
            }
        }
    }
}

@Composable
private fun BottomBattleSheet(
    state: PlayerUiState,
    expanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    onCastVote: (String) -> Unit,
    bottomReservedPadding: Dp,
    modifier: Modifier = Modifier,
) {
    val density = LocalDensity.current
    var guideExpanded by remember { mutableStateOf(false) }
    val dragThresholdPx = with(density) { 36.dp.toPx() }
    val dragDistance = remember { mutableFloatStateOf(0f) }
    val sheetDragState = rememberDraggableState { delta ->
        dragDistance.floatValue += delta
    }
    val sheetDragModifier = Modifier.draggable(
        orientation = Orientation.Vertical,
        state = sheetDragState,
        onDragStopped = {
            when {
                dragDistance.floatValue > dragThresholdPx -> onExpandedChange(false)
                dragDistance.floatValue < -dragThresholdPx -> onExpandedChange(true)
            }
            dragDistance.floatValue = 0f
        },
    )

    Surface(
        modifier = modifier
            .height(if (expanded) 390.dp else 0.dp)
            .then(sheetDragModifier),
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        color = LocalPlayerColors.current.nav,
        tonalElevation = 0.dp,
        shadowElevation = 0.dp,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        if (!expanded) return@Surface
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp, bottom = bottomReservedPadding),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .width(44.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(Color(0x44172033))
                    .then(sheetDragModifier)
                    .clickable { onExpandedChange(false) }
            )

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .then(sheetDragModifier)
                    .clickable { onExpandedChange(false) }
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "人气 PK",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "可用积分 ${state.availablePoints}",
                    color = LocalPlayerColors.current.muted,
                    style = MaterialTheme.typography.labelMedium,
                )
            }

            val dramaVoteEntries = state.voteBoard.filter { it.dramaTitle == state.drama?.title }
            val supportEntries = dramaVoteEntries.filter { it.track == VoteTrack.Support }
            val rageEntries = dramaVoteEntries.filter { it.track == VoteTrack.Rage }

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 14.dp, vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    color = LocalPlayerColors.current.surface,
                    border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { guideExpanded = !guideExpanded },
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                text = "玩法说明",
                                color = LocalPlayerColors.current.text,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                text = if (guideExpanded) "收起" else "展开",
                                color = Color(0xFFD99000),
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                        if (!guideExpanded) {
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "积分来源、投票消耗与 PK 规则",
                                color = LocalPlayerColors.current.muted,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                        if (guideExpanded) {
                            Spacer(modifier = Modifier.height(10.dp))
                            Column(
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Text(
                                    text = "一边看剧，一边把新收集到的积分投给喜欢的角色，或者把怒火值砸向最招恨的角色。",
                                    color = LocalPlayerColors.current.muted,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                                Text(
                                    text = "收下新高光卡 +1 分 · 收下新结局卡 +1 分 · 每投 1 票消耗 1 分",
                                    color = LocalPlayerColors.current.muted,
                                    style = MaterialTheme.typography.labelMedium,
                                )
                            }
                        }
                    }
                }

                if (dramaVoteEntries.isEmpty()) {
                    CompactBattleEmptyState(dramaTitle = state.drama?.title)
                } else {
                    if (supportEntries.isNotEmpty()) {
                        CompactVoteSection(
                            title = "人气值专区",
                            entries = supportEntries,
                            accent = Color(0xFFD99000),
                            buttonLabel = "投 1 票",
                            availablePoints = state.availablePoints,
                            onCastVote = onCastVote,
                        )
                    }

                    if (rageEntries.isNotEmpty()) {
                        CompactVoteSection(
                            title = "怒火值专区",
                            entries = rageEntries,
                            accent = Color(0xFFFF7A7A),
                            buttonLabel = "踩 1 票",
                            availablePoints = state.availablePoints,
                            onCastVote = onCastVote,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CompactBattleEmptyState(
    dramaTitle: String?,
) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = "暂无角色 PK",
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "${dramaTitle ?: "当前短剧"}还没有配置可投票角色。",
                color = LocalPlayerColors.current.muted,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun CompactLeaderCard(
    label: String,
    entry: VoteEntry,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        color = LocalPlayerColors.current.surface,
        border = BorderStroke(1.dp, accent.copy(alpha = 0.35f)),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = label,
                color = accent,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
            )
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RemoteImage(
                    imageUrl = entry.thumbnailUrl,
                    contentDescription = entry.name,
                    modifier = Modifier
                        .size(54.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(LocalPlayerColors.current.chip),
                    contentScale = ContentScale.Crop,
                )
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(
                        text = entry.name,
                        color = LocalPlayerColors.current.text,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = "${entry.votes} 票",
                        color = accent,
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun CompactVoteSection(
    title: String,
    entries: List<VoteEntry>,
    accent: Color,
    buttonLabel: String,
    availablePoints: Int,
    onCastVote: (String) -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = LocalPlayerColors.current.surfaceAlt,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = title,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            entries.forEach { entry ->
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = LocalPlayerColors.current.surfaceRaised,
                    border = BorderStroke(1.dp, LocalPlayerColors.current.border),
                ) {
                    Row(
                        modifier = Modifier.padding(10.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RemoteImage(
                            imageUrl = entry.thumbnailUrl,
                            contentDescription = entry.name,
                            modifier = Modifier
                                .size(56.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(LocalPlayerColors.current.chip),
                            contentScale = ContentScale.Crop,
                        )
                        Column(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(3.dp),
                        ) {
                            Text(
                                text = entry.name,
                                color = LocalPlayerColors.current.text,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                text = entry.headline,
                                color = accent,
                                style = MaterialTheme.typography.labelMedium,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                text = entry.description,
                                color = LocalPlayerColors.current.muted,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        Column(
                            horizontalAlignment = Alignment.End,
                            verticalArrangement = Arrangement.spacedBy(6.dp),
                        ) {
                            Text(
                                text = "${entry.votes} 票",
                                color = accent,
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold,
                            )
                            Surface(
                                modifier = Modifier.clickable(
                                    enabled = availablePoints > 0,
                                    onClick = { onCastVote(entry.key) },
                                ),
                                shape = RoundedCornerShape(999.dp),
                                color = if (availablePoints > 0) accent else LocalPlayerColors.current.chip,
                            ) {
                                Text(
                                    text = if (availablePoints > 0) buttonLabel else "积分不足",
                                    color = if (availablePoints > 0) Color(0xFF07111F) else Color(0x88FFFFFF),
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CollectionPreviewRow(
    title: String,
    subtitle: String,
    cards: List<CollectionCard>,
    category: CardCategory,
    accent: Color,
    totalCount: Int,
    onCardClick: (CollectionCard) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = title,
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = subtitle,
                    color = Color(0xFF93A5C8),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            StatusPill(label = "收集", value = "${cards.size}/$totalCount")
        }

        if (cards.isEmpty()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                EmptyCollectionCardBack(
                    category = category,
                    accent = accent,
                )
            }
        } else {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                cards.forEach { card ->
                    CollectionCardPreview(
                        card = card,
                        accent = accent,
                        onClick = { onCardClick(card) },
                    )
                }
            }
        }
    }
}

@Composable
private fun EmptyCollectionCardBack(
    category: CardCategory,
    accent: Color,
) {
    val previewAspectRatio = if (category == CardCategory.Highlight) 0.74f else 0.94f
    Surface(
        modifier = Modifier.width(158.dp),
        shape = RoundedCornerShape(20.dp),
        color = LocalPlayerColors.current.surfaceAlt,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(previewAspectRatio)
                    .clip(RoundedCornerShape(16.dp)),
            ) {
                CardBackImage(
                    category = category,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            Text(
                text = "待收集",
                color = accent,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "收下后这里显示卡面",
                color = LocalPlayerColors.current.muted,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun CollectionCardPreview(
    card: CollectionCard,
    accent: Color,
    onClick: () -> Unit,
) {
    val previewAspectRatio = if (card.category == CardCategory.Highlight) 0.74f else 0.94f
    Surface(
        modifier = Modifier
            .width(158.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(20.dp),
        color = LocalPlayerColors.current.surfaceAlt,
        border = BorderStroke(1.dp, LocalPlayerColors.current.border),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(previewAspectRatio)
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        Brush.verticalGradient(
                            colors = if (card.category == CardCategory.Highlight) {
                                listOf(Color(0xFFD99000), Color(0xFFFC8A4A))
                            } else {
                                listOf(Color(0xFFAA95FF), Color(0xFF4768FF))
                            }
                        )
                    ),
                contentAlignment = Alignment.Center,
            ) {
                RemoteImage(
                    imageUrl = card.imagePath,
                    contentDescription = card.title,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                )
            }
            Text(
                text = card.title,
                color = LocalPlayerColors.current.text,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = card.episodeName,
                color = accent,
                style = MaterialTheme.typography.labelMedium,
            )
        }
    }
}

@Composable
private fun CollectionCardDetailOverlay(
    card: CollectionCard,
    onClose: () -> Unit,
    initiallyShowingBack: Boolean = false,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    var flipped by remember(card.id, initiallyShowingBack) { mutableStateOf(initiallyShowingBack) }
    val rotation by animateFloatAsState(
        targetValue = if (flipped) 180f else 0f,
        animationSpec = tween(durationMillis = 420),
        label = "cardFlip",
    )
    val showBack = rotation > 90f
    val accent = if (card.category == CardCategory.Highlight) {
        Color(0xFFD99000)
    } else {
        Color(0xFF9B8BFF)
    }
    val detailAspectRatio = if (card.category == CardCategory.Highlight) 0.68f else 0.92f
    val detailWidthFraction = if (card.category == CardCategory.Highlight) 0.84f else 0.9f
    val colors = LocalPlayerColors.current
    val isLight = colors == LightPlayerColors
    val overlayBackground = if (isLight) colors.surface else Color(0xE6000000)
    val detailCardBorder = if (isLight) colors.border else Color(0x33FFFFFF)

    Box(
        modifier = modifier.background(overlayBackground),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 22.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                StatusPill(
                    label = if (card.category == CardCategory.Highlight) "高光卡" else "结局卡",
                    value = card.episodeName,
                )
                Surface(
                    modifier = Modifier.clickable(onClick = onClose),
                    shape = CircleShape,
                    color = colors.chip,
                    border = BorderStroke(1.dp, colors.border),
                ) {
                    Text(
                        text = "×",
                        color = colors.text,
                        fontSize = 24.sp,
                        modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
                    )
                }
            }

            Surface(
                modifier = Modifier
                    .fillMaxWidth(detailWidthFraction)
                    .aspectRatio(detailAspectRatio)
                    .graphicsLayer {
                        rotationY = rotation
                        cameraDistance = 12f * density
                },
                shape = RoundedCornerShape(24.dp),
                color = colors.surfaceAlt,
                border = BorderStroke(1.dp, detailCardBorder),
                shadowElevation = 14.dp,
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .graphicsLayer {
                            if (showBack) {
                                rotationY = 180f
                            }
                        }
                ) {
                    if (showBack) {
                        CardBackImage(
                            category = card.category,
                            modifier = Modifier
                                .fillMaxSize()
                                .clip(RoundedCornerShape(24.dp)),
                        )
                    } else {
                        RemoteImage(
                            imageUrl = card.imagePath,
                            contentDescription = card.title,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop,
                        )
                    }
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .clickable { flipped = !flipped },
                    )
                }
            }

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                Text(
                    text = if (showBack) "点击卡牌翻开" else card.title,
                    color = if (showBack) colors.text else accent,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                if (showBack || card.description.isNotBlank()) {
                    Text(
                        text = if (showBack) "卡背 · ${card.episodeName}" else card.description,
                        color = colors.text,
                        style = MaterialTheme.typography.bodyMedium,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Text(
                    text = if (showBack) "点击中间卡片翻开卡面" else "点击卡面可翻回卡背",
                    color = colors.muted,
                    style = MaterialTheme.typography.labelMedium,
                )
                if (!showBack && actionLabel != null && onAction != null) {
                    Button(onClick = onAction) {
                        Text(actionLabel)
                    }
                }
            }
        }
    }
}

@Composable
private fun CardBackImage(
    category: CardCategory,
    modifier: Modifier = Modifier,
) {
    val backUrl = if (category == CardCategory.Highlight) {
        HighlightCardBackUrl
    } else {
        EndingCardBackUrl
    }
    Box(
        modifier = modifier.background(Color(0xFF0C1222)),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF0B1020),
                            Color(0xFF162849),
                            Color(0xFF0C1222),
                        )
                    )
                )
        )
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 30.dp),
            verticalArrangement = Arrangement.SpaceBetween,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Surface(
                shape = RoundedCornerShape(999.dp),
                color = Color(0x26FFFFFF),
                border = BorderStroke(1.dp, LocalPlayerColors.current.border),
            ) {
                Text(
                    text = "Drama Card",
                    color = Color(0xFFD99000),
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                )
            }
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    text = "短剧高光卡",
                    color = LocalPlayerColors.current.text,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = "高光收藏 · 结局分支",
                    color = Color(0xFFB9C7E8),
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                )
            }
            Text(
                text = "点击翻转查看卡面",
                color = Color(0x99FFFFFF),
                style = MaterialTheme.typography.labelMedium,
            )
        }
        RemoteImage(
            imageUrl = backUrl,
            contentDescription = "卡背",
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )
    }
}

@Composable
private fun RemoteImage(
    imageUrl: String,
    contentDescription: String,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
) {
    val context = LocalContext.current
    var bitmap by remember(imageUrl) { mutableStateOf(ImageMemoryCache.images[imageUrl]?.bitmap) }

    LaunchedEffect(imageUrl) {
        if (imageUrl.isBlank()) return@LaunchedEffect
        ImageMemoryCache.images[imageUrl]?.let {
            bitmap = it.bitmap
            return@LaunchedEffect
        }
        bitmap = null
        val cachedImage = withContext(Dispatchers.IO) {
            loadCachedImage(context, imageUrl)
        }
        if (cachedImage != null) {
            ImageMemoryCache.images[imageUrl] = cachedImage
            bitmap = cachedImage.bitmap
        }
    }

    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center,
    ) {
        val loadedBitmap = bitmap
        if (loadedBitmap != null) {
            Image(
                bitmap = loadedBitmap,
                contentDescription = contentDescription,
                modifier = Modifier.fillMaxSize(),
                contentScale = contentScale,
            )
        } else {
            Text(
                text = "加载中",
                color = Color(0xCCFFFFFF),
                style = MaterialTheme.typography.labelMedium,
            )
        }
    }
}

private fun loadCachedImage(context: Context, imageUrl: String): CachedImage? {
    return runCatching {
        val decodedBitmap = when {
            imageUrl.startsWith("content://") -> {
                context.contentResolver.openInputStream(Uri.parse(imageUrl))?.use { input ->
                    BitmapFactory.decodeStream(input)
                }
            }

            imageUrl.startsWith("asset://") -> {
                val assetPath = imageUrl.removePrefix("asset://")
                context.assets.open(assetPath).use { input ->
                    BitmapFactory.decodeStream(input)
                }
            }

            else -> {
                URL(imageUrl).openStream().use { input ->
                    BitmapFactory.decodeStream(input)
                }
            }
        }
        decodedBitmap?.let {
            CachedImage(
                bitmap = it.asImageBitmap(),
                bytes = it.byteCount,
            )
        }
    }.getOrNull()
}

@Composable
private fun BottomNavBar(
    selectedTab: AppTab,
    onSelectTab: (AppTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalPlayerColors.current

    Column(
        modifier = modifier
            .background(colors.nav)
            .navigationBarsPadding()
            .padding(top = 8.dp, bottom = 12.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 18.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AppTab.entries.forEach { tab ->
                    NavItem(
                        label = tab.label,
                        selected = tab == selectedTab,
                        onClick = { onSelectTab(tab) },
                    )
                }
            }
        }
    }
}

@Composable
private fun NavItem(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier
            .width(56.dp)
            .clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        Text(
            text = if (selected) "●" else "○",
            color = if (selected) Color(0xFFD99000) else LocalPlayerColors.current.muted,
            style = MaterialTheme.typography.labelSmall,
        )
        Text(
            text = label,
            color = if (selected) LocalPlayerColors.current.text else LocalPlayerColors.current.muted,
            style = MaterialTheme.typography.labelLarge,
            fontWeight = if (selected) FontWeight.Bold else FontWeight.SemiBold,
            maxLines = 1,
            textAlign = TextAlign.Center,
        )
    }
}

private fun dramaCaption(state: PlayerUiState): String {
    return when (val overlay = state.overlayState) {
        is OverlayState.Highlight -> overlay.card.title
        is OverlayState.EndingResult -> overlay.card.title
        is OverlayState.EndingChoice -> overlay.episode.endingChoice?.question ?: "做出你的选择"
        OverlayState.None -> state.drama?.title ?: "短剧"
    }
}

private fun dramaSubCaption(state: PlayerUiState): String {
    return when (val overlay = state.overlayState) {
        is OverlayState.Highlight -> overlay.card.description
        is OverlayState.EndingResult -> overlay.card.description
        is OverlayState.EndingChoice -> "在剧情分叉点暂停，让用户选择后续走向，再把对应的漫画结局收进卡册。"
        OverlayState.None -> "${state.currentEpisode?.episodeName ?: ""}  完整正片播放中".trim()
    }
}

private val discoveryDramas = listOf(
    DramaShelfItem(
        title = "幸得相遇离婚时",
        subtitle = "都市情感",
        coverUrl = CoverXingdeUrl,
        episodeCount = 25,
    ),
    DramaShelfItem(
        title = "云渺1：我修仙多年强亿点怎么了",
        subtitle = "修仙逆袭",
        coverUrl = CoverYunmiaoUrl,
        episodeCount = 24,
    ),
    DramaShelfItem(
        title = "北往",
        subtitle = "年代情感",
        coverUrl = CoverBeiwangUrl,
        episodeCount = 19,
    ),
    DramaShelfItem(
        title = "北派寻宝笔记",
        subtitle = "悬疑寻宝",
        coverUrl = CoverBeipaiUrl,
        episodeCount = 19,
    ),
    DramaShelfItem(
        title = "十八岁太奶奶驾到，重整家族荣耀第三部",
        subtitle = "家族爽剧",
        coverUrl = CoverTainainaiUrl,
        episodeCount = 26,
    ),
    DramaShelfItem(
        title = "天下第一纨绔",
        subtitle = "古装逆袭",
        coverUrl = CoverWankuUrl,
        episodeCount = 24,
    ),
    DramaShelfItem(
        title = "家里家外",
        subtitle = "家庭情感",
        coverUrl = CoverJialijiawaiUrl,
        episodeCount = 24,
    ),
    DramaShelfItem(
        title = "撕夜",
        subtitle = "都市情感",
        coverUrl = CoverSiyeUrl,
        episodeCount = 23,
    ),
    DramaShelfItem(
        title = "荒年全村啃树皮，我有系统满仓肉",
        subtitle = "系统种田",
        coverUrl = CoverHuangnianUrl,
        episodeCount = 23,
    ),
    DramaShelfItem(
        title = "那年冬至",
        subtitle = "情感悬念",
        coverUrl = CoverDongzhiUrl,
        episodeCount = 25,
    ),
)

private fun coverUrlForDrama(title: String?): String {
    return when (title) {
        "北派寻宝笔记" -> CoverBeipaiUrl
        "云渺1：我修仙多年强亿点怎么了" -> CoverYunmiaoUrl
        "北往" -> CoverBeiwangUrl
        "十八岁太奶奶驾到，重整家族荣耀第三部" -> CoverTainainaiUrl
        "天下第一纨绔" -> CoverWankuUrl
        "家里家外" -> CoverJialijiawaiUrl
        "撕夜" -> CoverSiyeUrl
        "荒年全村啃树皮，我有系统满仓肉" -> CoverHuangnianUrl
        "那年冬至" -> CoverDongzhiUrl
        else -> CoverXingdeUrl
    }
}

private fun formatMs(value: Long): String {
    val totalSeconds = (value / 1000L).coerceAtLeast(0L)
    val minutes = totalSeconds / 60L
    val seconds = totalSeconds % 60L
    return "%d:%02d".format(minutes, seconds)
}
