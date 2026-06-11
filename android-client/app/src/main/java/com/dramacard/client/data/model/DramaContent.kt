package com.dramacard.client.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DramaContent(
    val title: String,
    val episodes: List<EpisodeContent>,
)

@Serializable
data class EpisodeContent(
    val episodeName: String,
    val videoPath: String,
    val highlights: List<HighlightCard> = emptyList(),
    val endingChoice: EndingChoice? = null,
)

@Serializable
data class HighlightCard(
    val id: String,
    val startAtSec: Double? = null,
    val triggerAtSec: Double,
    val pauseAtSec: Double? = null,
    val title: String,
    val description: String,
    val emotion: String,
    val starLevel: Int,
    val imagePath: String,
)

@Serializable
data class EndingChoice(
    val startAtSec: Double? = null,
    val triggerAtSec: Double,
    val pauseAtSec: Double? = null,
    val question: String,
    val branches: List<EndingBranch>,
)

@Serializable
data class EndingBranch(
    val optionId: String,
    val optionLabel: String,
    val cardTitle: String,
    val cardDescription: String,
    val comicPath: String,
)

@Serializable
data class CollectionCard(
    val id: String,
    val dramaTitle: String,
    val episodeName: String,
    val title: String,
    val description: String,
    val imagePath: String,
    val category: CardCategory,
)

@Serializable
enum class CardCategory {
    @SerialName("highlight")
    Highlight,

    @SerialName("ending")
    Ending,
}
