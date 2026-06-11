package com.dramacard.client.player

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.dramacard.client.data.model.CardCategory
import com.dramacard.client.data.model.CollectionCard
import com.dramacard.client.data.model.EndingBranch
import com.dramacard.client.data.model.EpisodeContent
import com.dramacard.client.data.model.HighlightCard
import com.dramacard.client.data.repo.LocalDramaRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

class PlayerViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val repository = LocalDramaRepository()
    private val dramaTitles = repository.availableDramaTitles()
    private val preferences = application.getSharedPreferences("dramacard_player_state", Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    private val _uiState = MutableStateFlow(PlayerUiState())
    val uiState: StateFlow<PlayerUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val persisted = loadPersistedState()
            val dramaTitle = persisted.currentDramaTitle?.takeIf { it in dramaTitles } ?: dramaTitles.first()
            val drama = repository.loadDramaContent(application, dramaTitle)
            val targetEpisode = persisted.currentEpisodeName?.let { episodeName ->
                drama.episodes.firstOrNull { it.episodeName == episodeName }
            } ?: drama.episodes.firstOrNull()

            applyState(
                PlayerUiState(
                    isLoading = false,
                    drama = drama,
                    currentEpisode = targetEpisode,
                    profileName = persisted.profileName,
                    profileAvatarIndex = persisted.profileAvatarIndex,
                    profileAvatarUri = persisted.profileAvatarUri,
                    highlightCards = persisted.highlightCards,
                    endingCards = persisted.endingCards,
                    availablePoints = persisted.availablePoints,
                    supportVotesCast = persisted.supportVotesCast,
                    rageVotesCast = persisted.rageVotesCast,
                    likedEpisodes = persisted.likedEpisodes,
                    favoritedDramaTitles = persisted.favoritedDramaTitles,
                    watchHistory = if (persisted.watchHistory.isNotEmpty()) {
                        persisted.watchHistory
                    } else {
                        targetEpisode?.let { listOf(WatchHistoryEntry(drama.title, it.episodeName)) }.orEmpty()
                    },
                    voteBoard = mergeVotes(defaultVoteBoard(), persisted.voteBoard),
                )
            )
        }
    }

    fun selectEpisode(episode: EpisodeContent) {
        val dramaTitle = _uiState.value.drama?.title ?: return
        updateState { current ->
            current.copy(
                currentEpisode = episode,
                overlayState = OverlayState.None,
                watchHistory = mergeWatchHistory(
                    current = current.watchHistory,
                    entry = WatchHistoryEntry(dramaTitle, episode.episodeName),
                ),
            )
        }
    }

    fun selectDrama(title: String) {
        viewModelScope.launch {
            val drama = repository.loadDramaContent(getApplication(), title)
            val firstEpisode = drama.episodes.firstOrNull()
            updateState { current ->
                current.copy(
                    drama = drama,
                    currentEpisode = firstEpisode,
                    overlayState = OverlayState.None,
                    watchHistory = firstEpisode?.let { episode ->
                        mergeWatchHistory(
                            current = current.watchHistory,
                            entry = WatchHistoryEntry(drama.title, episode.episodeName),
                        )
                    } ?: current.watchHistory,
                )
            }
        }
    }

    fun openDramaEpisode(title: String, episodeName: String? = null) {
        viewModelScope.launch {
            val drama = repository.loadDramaContent(getApplication(), title)
            val targetEpisode = episodeName?.let { name ->
                drama.episodes.firstOrNull { it.episodeName == name }
            } ?: drama.episodes.firstOrNull()
            updateState { current ->
                current.copy(
                    drama = drama,
                    currentEpisode = targetEpisode,
                    overlayState = OverlayState.None,
                    watchHistory = targetEpisode?.let { episode ->
                        mergeWatchHistory(
                            current = current.watchHistory,
                            entry = WatchHistoryEntry(drama.title, episode.episodeName),
                        )
                    } ?: current.watchHistory,
                )
            }
        }
    }

    fun nextDrama() {
        val currentTitle = _uiState.value.drama?.title ?: return
        val currentIndex = dramaTitles.indexOf(currentTitle).takeIf { it >= 0 } ?: return
        val nextTitle = dramaTitles[(currentIndex + 1) % dramaTitles.size]
        selectDrama(nextTitle)
    }

    fun previousDrama() {
        val currentTitle = _uiState.value.drama?.title ?: return
        val currentIndex = dramaTitles.indexOf(currentTitle).takeIf { it >= 0 } ?: return
        val previousTitle = dramaTitles[(currentIndex - 1 + dramaTitles.size) % dramaTitles.size]
        selectDrama(previousTitle)
    }

    fun previewCurrentHighlight() {
        val episode = _uiState.value.currentEpisode ?: return
        val highlight = episode.highlights.firstOrNull() ?: return
        showHighlightCard(episode, highlight)
    }

    fun previewHighlight(highlightId: String) {
        val episode = _uiState.value.currentEpisode ?: return
        val highlight = episode.highlights.firstOrNull { it.id == highlightId } ?: return
        showHighlightCard(episode, highlight)
    }

    fun previewEndingChoice() {
        val episode = _uiState.value.currentEpisode ?: return
        if (episode.endingChoice != null) {
            updateState { current ->
                current.copy(overlayState = OverlayState.EndingChoice(episode))
            }
        }
    }

    fun chooseEndingBranch(branch: EndingBranch) {
        val episode = _uiState.value.currentEpisode ?: return
        val dramaTitle = _uiState.value.drama?.title ?: return
        val card = toEndingCard(
            dramaTitle = dramaTitle,
            episodeName = episode.episodeName,
            title = branch.cardTitle,
            description = branch.cardDescription,
            imagePath = branch.comicPath,
        )
        collectEndingCard(card)
    }

    fun collectHighlightCard(card: CollectionCard) {
        val current = _uiState.value
        val isNew = current.highlightCards.none { it.id == card.id }
        applyState(
            current.copy(
                highlightCards = (current.highlightCards + card).distinctBy { it.id },
                overlayState = OverlayState.Highlight(card),
                availablePoints = current.availablePoints + if (isNew) 1 else 0,
            )
        )
    }

    fun collectEndingCard(card: CollectionCard) {
        val current = _uiState.value
        val isNew = current.endingCards.none { it.id == card.id }
        applyState(
            current.copy(
                endingCards = (current.endingCards + card).distinctBy { it.id },
                overlayState = OverlayState.EndingResult(card),
                availablePoints = current.availablePoints + if (isNew) 1 else 0,
            )
        )
    }

    fun castVote(targetKey: String) {
        val current = _uiState.value
        if (current.availablePoints <= 0) return
        val target = current.voteBoard.firstOrNull { it.key == targetKey } ?: return
        applyState(
            current.copy(
                availablePoints = current.availablePoints - 1,
                supportVotesCast = current.supportVotesCast + if (target.track == VoteTrack.Support) 1 else 0,
                rageVotesCast = current.rageVotesCast + if (target.track == VoteTrack.Rage) 1 else 0,
                voteBoard = current.voteBoard.map { entry ->
                    if (entry.key == targetKey) entry.copy(votes = entry.votes + 1) else entry
                },
            )
        )
    }

    fun toggleLikeCurrentEpisode() {
        val current = _uiState.value
        val title = current.drama?.title ?: return
        val episodeName = current.currentEpisode?.episodeName ?: return
        val target = WatchHistoryEntry(title, episodeName)
        val exists = current.likedEpisodes.any {
            it.dramaTitle == title && it.episodeName == episodeName
        }
        val next = if (exists) {
            current.likedEpisodes.filterNot {
                it.dramaTitle == title && it.episodeName == episodeName
            }
        } else {
            listOf(target) + current.likedEpisodes.filterNot {
                it.dramaTitle == title && it.episodeName == episodeName
            }
        }
        applyState(current.copy(likedEpisodes = next))
    }

    fun toggleFavoriteCurrentDrama() {
        val current = _uiState.value
        val title = current.drama?.title ?: return
        val next = current.favoritedDramaTitles.toMutableSet().apply {
            if (!add(title)) remove(title)
        }
        applyState(current.copy(favoritedDramaTitles = next))
    }

    fun cycleProfileAvatar() {
        val current = _uiState.value
        applyState(current.copy(profileAvatarIndex = (current.profileAvatarIndex + 1) % 5))
    }

    fun updateProfileAvatar(uri: String?) {
        updateState { current -> current.copy(profileAvatarUri = uri) }
    }

    fun updateProfileName(name: String) {
        val normalized = name.trim().ifEmpty { "短剧玩家" }.take(12)
        updateState { current -> current.copy(profileName = normalized) }
    }

    fun dismissOverlay() {
        updateState { current -> current.copy(overlayState = OverlayState.None) }
    }

    fun toHighlightCard(
        dramaTitle: String,
        episodeName: String,
        title: String,
        description: String,
        imagePath: String,
    ): CollectionCard {
        return CollectionCard(
            id = "highlight_${dramaTitle}_$episodeName$title",
            dramaTitle = dramaTitle,
            episodeName = episodeName,
            title = title,
            description = description,
            imagePath = imagePath,
            category = CardCategory.Highlight,
        )
    }

    fun toEndingCard(
        dramaTitle: String,
        episodeName: String,
        title: String,
        description: String,
        imagePath: String,
    ): CollectionCard {
        return CollectionCard(
            id = "ending_${dramaTitle}_$episodeName$title",
            dramaTitle = dramaTitle,
            episodeName = episodeName,
            title = title,
            description = description,
            imagePath = imagePath,
            category = CardCategory.Ending,
        )
    }

    private fun showHighlightCard(
        episode: EpisodeContent,
        highlight: HighlightCard,
    ) {
        val dramaTitle = _uiState.value.drama?.title ?: return
        updateState { current ->
            current.copy(
                overlayState = OverlayState.Highlight(
                    toHighlightCard(
                        dramaTitle = dramaTitle,
                        episodeName = episode.episodeName,
                        title = highlight.title,
                        description = highlight.description,
                        imagePath = highlight.imagePath,
                    )
                )
            )
        }
    }

    private fun applyState(state: PlayerUiState) {
        _uiState.value = state
        persistState(state)
    }

    private fun updateState(transform: (PlayerUiState) -> PlayerUiState) {
        applyState(transform(_uiState.value))
    }

    private fun mergeVotes(
        defaults: List<VoteEntry>,
        persisted: List<PersistedVoteCounter>,
    ): List<VoteEntry> {
        val persistedMap = persisted.associateBy { it.key }
        return defaults.map { entry ->
            entry.copy(votes = persistedMap[entry.key]?.votes ?: entry.votes)
        }
    }

    private fun persistState(state: PlayerUiState) {
        val payload = PersistedPlayerState(
            currentDramaTitle = state.drama?.title,
            currentEpisodeName = state.currentEpisode?.episodeName,
            profileName = state.profileName,
            profileAvatarIndex = state.profileAvatarIndex,
            profileAvatarUri = state.profileAvatarUri,
            highlightCards = state.highlightCards,
            endingCards = state.endingCards,
            availablePoints = state.availablePoints,
            supportVotesCast = state.supportVotesCast,
            rageVotesCast = state.rageVotesCast,
            likedEpisodes = state.likedEpisodes,
            favoritedDramaTitles = state.favoritedDramaTitles,
            watchHistory = state.watchHistory,
            voteBoard = state.voteBoard.map { PersistedVoteCounter(it.key, it.votes) },
        )
        preferences.edit().putString("player_state_json", json.encodeToString(payload)).apply()
    }

    private fun loadPersistedState(): PersistedPlayerState {
        val raw = preferences.getString("player_state_json", null) ?: return PersistedPlayerState()
        return runCatching {
            json.decodeFromString<PersistedPlayerState>(raw)
        }.getOrDefault(PersistedPlayerState())
    }

    private fun mergeWatchHistory(
        current: List<WatchHistoryEntry>,
        entry: WatchHistoryEntry,
    ): List<WatchHistoryEntry> {
        return listOf(entry) + current.filterNot {
            it.dramaTitle == entry.dramaTitle && it.episodeName == entry.episodeName
        }.take(11)
    }

    @Serializable
    private data class PersistedVoteCounter(
        val key: String,
        val votes: Int,
    )

    @Serializable
    private data class PersistedPlayerState(
        val currentDramaTitle: String? = null,
        val currentEpisodeName: String? = null,
        val profileName: String = "短剧玩家",
        val profileAvatarIndex: Int = 0,
        val profileAvatarUri: String? = null,
        val highlightCards: List<CollectionCard> = emptyList(),
        val endingCards: List<CollectionCard> = emptyList(),
        val availablePoints: Int = 0,
        val supportVotesCast: Int = 0,
        val rageVotesCast: Int = 0,
        val likedEpisodes: List<WatchHistoryEntry> = emptyList(),
        val favoritedDramaTitles: Set<String> = emptySet(),
        val watchHistory: List<WatchHistoryEntry> = emptyList(),
        val voteBoard: List<PersistedVoteCounter> = emptyList(),
    )
}
