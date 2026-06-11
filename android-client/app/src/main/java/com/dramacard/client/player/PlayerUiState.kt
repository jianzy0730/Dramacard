package com.dramacard.client.player

import com.dramacard.client.data.model.CollectionCard
import com.dramacard.client.data.model.DramaContent
import com.dramacard.client.data.model.EpisodeContent
import kotlinx.serialization.Serializable

enum class VoteTrack {
    Support,
    Rage,
}

@Serializable
data class VoteEntry(
    val key: String,
    val dramaTitle: String,
    val name: String,
    val track: VoteTrack,
    val votes: Int = 0,
    val description: String,
    val headline: String,
    val thumbnailUrl: String,
)

sealed interface OverlayState {
    data object None : OverlayState
    data class Highlight(val card: CollectionCard) : OverlayState
    data class EndingChoice(val episode: EpisodeContent) : OverlayState
    data class EndingResult(val card: CollectionCard) : OverlayState
}

@Serializable
data class WatchHistoryEntry(
    val dramaTitle: String,
    val episodeName: String,
)

data class PlayerUiState(
    val isLoading: Boolean = true,
    val drama: DramaContent? = null,
    val currentEpisode: EpisodeContent? = null,
    val profileName: String = "短剧玩家",
    val profileAvatarIndex: Int = 0,
    val profileAvatarUri: String? = null,
    val overlayState: OverlayState = OverlayState.None,
    val highlightCards: List<CollectionCard> = emptyList(),
    val endingCards: List<CollectionCard> = emptyList(),
    val availablePoints: Int = 0,
    val supportVotesCast: Int = 0,
    val rageVotesCast: Int = 0,
    val likedEpisodes: List<WatchHistoryEntry> = emptyList(),
    val favoritedDramaTitles: Set<String> = emptySet(),
    val watchHistory: List<WatchHistoryEntry> = emptyList(),
    val voteBoard: List<VoteEntry> = defaultVoteBoard(),
)

private const val CharacterCardBaseUrl = "https://example.com/dramacard-assets/characters"

internal fun defaultVoteBoard(): List<VoteEntry> = listOf(
    VoteEntry(
        key = "beipai_xiang_yunfeng",
        dramaTitle = "北派寻宝笔记",
        name = "项云峰",
        track = VoteTrack.Support,
        description = "为项云峰的胆识、眼力和一路成长投出支持票。",
        headline = "北派人气冲榜候选",
        thumbnailUrl = "$CharacterCardBaseUrl/beipai_xiang_yunfeng.png",
    ),
    VoteEntry(
        key = "beipai_wang_xiansheng",
        dramaTitle = "北派寻宝笔记",
        name = "王显生",
        track = VoteTrack.Support,
        description = "为王显生的沉稳带队、老练判断和关键兜底投出支持票。",
        headline = "北派高人气领队",
        thumbnailUrl = "$CharacterCardBaseUrl/beipai_wang_xiansheng.png",
    ),
    VoteEntry(
        key = "beipai_yinhu",
        dramaTitle = "北派寻宝笔记",
        name = "银狐",
        track = VoteTrack.Support,
        description = "为银狐的江湖经验、暗线提醒和师长气场投出支持票。",
        headline = "北派神秘助力",
        thumbnailUrl = "$CharacterCardBaseUrl/beipai_yinhu.png",
    ),
    VoteEntry(
        key = "beipai_sun_laoer",
        dramaTitle = "北派寻宝笔记",
        name = "孙老二",
        track = VoteTrack.Support,
        description = "为孙老二的一线行动力、实干劲和可靠配合投出支持票。",
        headline = "北派行动派",
        thumbnailUrl = "$CharacterCardBaseUrl/beipai_sun_laoer.png",
    ),
    VoteEntry(
        key = "beipai_sun_laosan",
        dramaTitle = "北派寻宝笔记",
        name = "孙老三",
        track = VoteTrack.Support,
        description = "为孙老三的冲劲、机警和现场反应投出支持票。",
        headline = "北派冲锋位",
        thumbnailUrl = "$CharacterCardBaseUrl/beipai_sun_laosan.png",
    ),
    VoteEntry(
        key = "tang_ying",
        dramaTitle = "幸得相遇离婚时",
        name = "唐颖",
        track = VoteTrack.Support,
        description = "为唐颖的重生、反击和坚持投出支持票。",
        headline = "幸得人气冲榜候选",
        thumbnailUrl = "$CharacterCardBaseUrl/xingde_tang_ying.png",
    ),
    VoteEntry(
        key = "jiang_ciyun",
        dramaTitle = "幸得相遇离婚时",
        name = "江辞云",
        track = VoteTrack.Support,
        description = "为江辞云的守护、兜底和深情投出支持票。",
        headline = "幸得高人气守护者",
        thumbnailUrl = "$CharacterCardBaseUrl/xingde_jiang_ciyun.png",
    ),
    VoteEntry(
        key = "lu_li",
        dramaTitle = "幸得相遇离婚时",
        name = "陆励",
        track = VoteTrack.Rage,
        description = "把怒火值砸向陆励，为背叛、害胎和算计记一笔。",
        headline = "最招恨候选",
        thumbnailUrl = "$CharacterCardBaseUrl/xingde_lu_li.png",
    ),
    VoteEntry(
        key = "xiao_li",
        dramaTitle = "幸得相遇离婚时",
        name = "小黎",
        track = VoteTrack.Rage,
        description = "把怒火值砸向小黎，为挑衅、下药和上位野心记一笔。",
        headline = "怒火值飙升角色",
        thumbnailUrl = "$CharacterCardBaseUrl/xingde_xiao_li.png",
    ),
)
