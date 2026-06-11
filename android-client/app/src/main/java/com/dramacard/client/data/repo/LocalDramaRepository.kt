package com.dramacard.client.data.repo

import android.content.Context
import com.dramacard.client.data.model.DramaContent
import com.dramacard.client.data.model.EndingBranch
import com.dramacard.client.data.model.EndingChoice
import com.dramacard.client.data.model.EpisodeContent
import com.dramacard.client.data.model.HighlightCard
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

class LocalDramaRepository : DramaRepository {
    private companion object {
        const val localBaseUrl = "http://10.0.2.2:8002"
        const val publicCosBaseUrl = "https://example.com/dramacard-assets"
        const val xingdeAssetBaseUrl =
            "$publicCosBaseUrl/%E5%B9%B8%E5%BE%97%E7%9B%B8%E9%81%87%E7%A6%BB%E5%A9%9A%E6%97%B6"
        const val beipaiAssetBaseUrl =
            "$publicCosBaseUrl/%E5%8C%97%E6%B4%BE%E5%AF%BB%E5%AE%9D%E7%AC%94%E8%AE%B0"
    }

    override suspend fun loadDramaContent(context: Context): DramaContent {
        return loadDramaContent(context, "幸得相遇离婚时")
    }

    fun availableDramaTitles(): List<String> = dramaSpecs.map { it.title }

    suspend fun loadDramaContent(context: Context, title: String): DramaContent {
        val spec = dramaSpecs.firstOrNull { it.title == title } ?: dramaSpecs.first()
        return DramaContent(
            title = spec.title,
            episodes = spec.episodeNumbers.map { number ->
                episode(
                    number = number,
                    videoPath = resolveVideoPath(spec, number),
                    highlights = when (spec.title) {
                        "幸得相遇离婚时" -> highlightsByEpisode[number].orEmpty()
                        "北派寻宝笔记" -> beipaiHighlightsByEpisode[number].orEmpty()
                        else -> emptyList()
                    },
                    endingChoice = when (spec.title) {
                        "幸得相遇离婚时" -> endingsByEpisode[number]
                        "北派寻宝笔记" -> beipaiEndingsByEpisode[number]
                        else -> null
                    },
                )
            },
        )
    }

    private fun resolveVideoPath(spec: DramaSpec, number: Int): String {
        spec.cosFolderName?.let { folderName ->
            val encodedFolder = urlEncodePathSegment(folderName)
            val encodedFile = urlEncodePathSegment("第${number}集.mp4")
            return "$publicCosBaseUrl/$encodedFolder/$encodedFile"
        }
        return "$localBaseUrl/${spec.slug}_ep_$number.mp4"
    }

    private data class DramaSpec(
        val title: String,
        val slug: String,
        val episodeNumbers: IntRange,
        val cosFolderName: String? = null,
    )

    private val dramaSpecs = listOf(
        DramaSpec("幸得相遇离婚时", "xingde", 1..25, "幸得相遇离婚时"),
        DramaSpec("北派寻宝笔记", "beipai", 63..81, "北派寻宝笔记"),
        DramaSpec("云渺1：我修仙多年强亿点怎么了", "yunmiao", 1..24, "云渺1：我修仙多年强亿点怎么了"),
        DramaSpec("北往", "beiwang", 1..19, "北往"),
        DramaSpec("十八岁太奶奶驾到，重整家族荣耀第三部", "tainainai", 1..26, "十八岁太奶奶驾到，重整家族荣耀第三部"),
        DramaSpec("天下第一纨绔", "wanku", 1..24, "天下第一纨绔"),
        DramaSpec("家里家外", "jialijiawai", 1..24, "家里家外"),
        DramaSpec("撕夜", "siye", 1..23, "撕夜"),
        DramaSpec("荒年全村啃树皮，我有系统满仓肉", "huangnian", 1..23, "荒年全村啃树皮，我有系统满仓肉"),
        DramaSpec("那年冬至", "dongzhi", 1..25, "那年冬至"),
    )

    private fun urlEncodePathSegment(value: String): String {
        return URLEncoder.encode(value, StandardCharsets.UTF_8.toString()).replace("+", "%20")
    }

    private fun episode(
        number: Int,
        videoPath: String,
        highlights: List<HighlightCard>,
        endingChoice: EndingChoice?,
    ): EpisodeContent {
        val episodeName = "第${number}集"
        return EpisodeContent(
            episodeName = episodeName,
            videoPath = videoPath,
            highlights = highlights,
            endingChoice = endingChoice,
        )
    }

    private fun highlight(
        id: String,
        cardIndex: Int,
        startAt: Double,
        triggerAt: Double,
        pauseAt: Double,
        title: String,
        description: String,
        emotion: String,
    ): HighlightCard {
        val imagePath = if (cardIndex >= 8) {
            "$xingdeAssetBaseUrl/highlight/%E5%8D%A1$cardIndex.jpeg"
        } else {
            "$xingdeAssetBaseUrl/highlight/card_${cardIndex.toString().padStart(2, '0')}.jpeg"
        }
        return HighlightCard(
            id = id,
            startAtSec = startAt,
            triggerAtSec = triggerAt,
            pauseAtSec = pauseAt,
            title = title,
            description = description,
            emotion = emotion,
            starLevel = 3,
            imagePath = imagePath,
        )
    }

    private fun localHighlight(
        id: String,
        imageAsset: String,
        startAt: Double,
        triggerAt: Double,
        pauseAt: Double,
        title: String,
        description: String,
        emotion: String,
    ): HighlightCard {
        return HighlightCard(
            id = id,
            startAtSec = startAt,
            triggerAtSec = triggerAt,
            pauseAtSec = pauseAt,
            title = title,
            description = description,
            emotion = emotion,
            starLevel = 3,
            imagePath = "asset://highlights/$imageAsset",
        )
    }

    private fun beipaiHighlight(
        id: String,
        cardIndex: Int,
        startAt: Double,
        triggerAt: Double,
        pauseAt: Double,
        title: String,
    ): HighlightCard {
        return HighlightCard(
            id = id,
            startAtSec = startAt,
            triggerAtSec = triggerAt,
            pauseAtSec = pauseAt,
            title = title,
            description = "",
            emotion = "",
            starLevel = 3,
            imagePath = "$beipaiAssetBaseUrl/%E5%8D%A1%E7%89%87/%E5%8D%A1$cardIndex.png",
        )
    }

    private fun endingChoice(
        episodeNumber: Int,
        triggerAt: Double,
        pauseAt: Double,
        question: String,
        aLabel: String,
        aTitle: String,
        aDescription: String,
        bLabel: String,
        bTitle: String,
        bDescription: String,
    ): EndingChoice {
        val ep = episodeNumber.toString().padStart(2, '0')
        return EndingChoice(
            startAtSec = (triggerAt - 12.0).coerceAtLeast(0.0),
            triggerAtSec = triggerAt,
            pauseAtSec = pauseAt,
            question = question,
            branches = listOf(
                EndingBranch(
                    optionId = "A",
                    optionLabel = aLabel,
                    cardTitle = aTitle,
                    cardDescription = aDescription,
                    comicPath = "$xingdeAssetBaseUrl/ending/ep_${ep}_A.png",
                ),
                EndingBranch(
                    optionId = "B",
                    optionLabel = bLabel,
                    cardTitle = bTitle,
                    cardDescription = bDescription,
                    comicPath = "$xingdeAssetBaseUrl/ending/ep_${ep}_B.png",
                ),
            ),
        )
    }

    private fun beipaiEndingChoice(
        episodeNumber: Int,
        triggerAt: Double,
        pauseAt: Double,
        question: String,
        aLabel: String,
        aTitle: String,
        aDescription: String,
        bLabel: String,
        bTitle: String,
        bDescription: String,
    ): EndingChoice {
        val encodedEpisode = urlEncodePathSegment("第${episodeNumber}集")
        val comicBaseUrl = "$beipaiAssetBaseUrl/%E7%BB%93%E5%B1%80%E6%BC%AB%E7%94%BB/$encodedEpisode"
        return EndingChoice(
            startAtSec = (triggerAt - 12.0).coerceAtLeast(0.0),
            triggerAtSec = triggerAt,
            pauseAtSec = pauseAt,
            question = question,
            branches = listOf(
                EndingBranch(
                    optionId = "A",
                    optionLabel = aLabel,
                    cardTitle = aTitle,
                    cardDescription = aDescription,
                    comicPath = "$comicBaseUrl/ending_A_ai.png",
                ),
                EndingBranch(
                    optionId = "B",
                    optionLabel = bLabel,
                    cardTitle = bTitle,
                    cardDescription = bDescription,
                    comicPath = "$comicBaseUrl/ending_B_ai.png",
                ),
            ),
        )
    }

    private val episodeTitles = listOf(
        1 to "小黎催陆励尽快和唐颖离婚",
        2 to "嚣张富二代当众放低俗台词骚扰孕妇",
        3 to "提问者两次灵魂拷问戳破完美婚姻表层假象",
        4 to "江辞云送唐颖回家，车内一句玩笑刺破分寸感",
        5 to "开篇亲密关系信任拷问，直接抛出通话对象质疑",
        6 to "剧情反转 此前所有谋害密谋原来只是唐颖的噩梦",
        7 to "闺蜜提前备齐男女款婴儿衣物，约定当茵茵孩子的干妈",
        8 to "女方看到匿名买单者的脸瞬间震惊",
        9 to "孕妻亮明已婚孕妇身份硬刚纠缠者",
        10 to "唐颖硬气怼走偏执纠缠男性",
        11 to "纠缠男性正式告别唐颖，表态后会无期",
        12 to "陆励绝情摊牌，直言娶唐颖是一时昏头",
        13 to "江辞云向唐颖承诺，受了委屈随时都能来找他",
        14 to "唐颖为救重病父亲被迫妥协，含泪签下离婚协议",
        15 to "高预算核心客户江先生背景曝光",
        16 to "小黎当众质疑唐颖想和陆励旧情复燃",
        17 to "小黎当众撒泼羞辱唐颖，把旧账和恶意一起掀开",
        18 to "江辞云说唐颖受了委屈随时来找他，唐颖却说再也不信任何人",
        19 to "唐颖开篇直接和对方划清边界",
        20 to "江辞云直球求婚，承诺帮唐颖讨回公道",
        21 to "江辞云下达反常收购指令，要求三天内完成亏损天濮公司的收购",
        22 to "江辞云当众硬刚包办婚约否认母亲指定的未婚妻",
        23 to "离异女性自爆婚史流产经历直面情感自卑",
        24 to "离婚后父亲向女儿敞开永远的后盾",
        25 to "唐颖哭诉把一生托付给陆励，却被他亲手毁掉整个家",
    )

    private val highlightsByEpisode = mapOf(
        1 to listOf(
            highlight(
                id = "h001_03",
                cardIndex = 1,
                startAt = 111.167,
                triggerAt = 116.15,
                pauseAt = 116.62,
                title = "回国",
                description = "",
                emotion = "",
            )
        ),
        2 to listOf(
            highlight(
                id = "h002_04",
                cardIndex = 8,
                startAt = 53.833,
                triggerAt = 65.067,
                pauseAt = 65.454,
                title = "压制",
                description = "",
                emotion = "",
            )
        ),
        3 to listOf(
            highlight(
                id = "h003_03",
                cardIndex = 9,
                startAt = 70.0,
                triggerAt = 100.733,
                pauseAt = 101.12,
                title = "假面",
                description = "",
                emotion = "",
            )
        ),
        5 to listOf(
            highlight(
                id = "h005_03",
                cardIndex = 10,
                startAt = 41.667,
                triggerAt = 66.15,
                pauseAt = 66.62,
                title = "誓言",
                description = "",
                emotion = "",
            )
        ),
        6 to listOf(
            highlight(
                id = "h006_04",
                cardIndex = 2,
                startAt = 134.0,
                triggerAt = 152.65,
                pauseAt = 153.12,
                title = "噩梦",
                description = "",
                emotion = "",
            )
        ),
        9 to listOf(
            highlight(
                id = "h009_01",
                cardIndex = 3,
                startAt = 118.167,
                triggerAt = 133.317,
                pauseAt = 133.787,
                title = "发卡",
                description = "",
                emotion = "",
            )
        ),
        13 to listOf(
            highlight(
                id = "h013_03",
                cardIndex = 4,
                startAt = 49.333,
                triggerAt = 58.333,
                pauseAt = 58.787,
                title = "守护",
                description = "",
                emotion = "",
            )
        ),
        17 to listOf(
            highlight(
                id = "h017_01",
                cardIndex = 5,
                startAt = 12.667,
                triggerAt = 27.8,
                pauseAt = 28.12,
                title = "冲突",
                description = "",
                emotion = "",
            )
        ),
        22 to listOf(
            highlight(
                id = "h022_03",
                cardIndex = 6,
                startAt = 80.667,
                triggerAt = 84.15,
                pauseAt = 84.62,
                title = "拒婚",
                description = "",
                emotion = "",
            )
        ),
        25 to listOf(
            highlight(
                id = "h025_03",
                cardIndex = 7,
                startAt = 119.167,
                triggerAt = 138.484,
                pauseAt = 138.954,
                title = "守护",
                description = "",
                emotion = "",
            )
        ),
    )

    private val beipaiHighlightsByEpisode = mapOf(
        64 to listOf(
            beipaiHighlight(
                id = "bp064_01",
                cardIndex = 1,
                startAt = 33.833,
                triggerAt = 40.0,
                pauseAt = 40.667,
                title = "破局",
            )
        ),
        65 to listOf(
            beipaiHighlight(
                id = "bp065_01",
                cardIndex = 2,
                startAt = 65.167,
                triggerAt = 80.833,
                pauseAt = 84.0,
                title = "入门",
            )
        ),
        66 to listOf(
            beipaiHighlight(
                id = "bp066_01",
                cardIndex = 3,
                startAt = 83.0,
                triggerAt = 86.0,
                pauseAt = 88.167,
                title = "龙穴",
            )
        ),
        67 to listOf(
            beipaiHighlight(
                id = "bp067_01",
                cardIndex = 4,
                startAt = 82.0,
                triggerAt = 94.167,
                pauseAt = 106.334,
                title = "奇楠",
            )
        ),
        69 to listOf(
            beipaiHighlight(
                id = "bp069_01",
                cardIndex = 5,
                startAt = 61.333,
                triggerAt = 72.0,
                pauseAt = 75.5,
                title = "行宫",
            )
        ),
        70 to listOf(
            beipaiHighlight(
                id = "bp070_01",
                cardIndex = 6,
                startAt = 95.5,
                triggerAt = 99.167,
                pauseAt = 100.167,
                title = "惊变",
            )
        ),
        81 to listOf(
            beipaiHighlight(
                id = "bp081_01",
                cardIndex = 7,
                startAt = 155.167,
                triggerAt = 169.0,
                pauseAt = 192.0,
                title = "救哥",
            )
        ),
    )

    private val beipaiEndingsByEpisode = mapOf(
        63 to beipaiEndingChoice(
            episodeNumber = 63,
            triggerAt = 294.0,
            pauseAt = 294.0,
            question = "你刚拿到给奶奶治病的四千块救命钱，面对不明人员厉声呵斥要求你立刻滚出潘家园，你会怎么选？",
            aLabel = "暂时隐忍，先带着钱离开潘家园避风头",
            aTitle = "退让",
            aDescription = "项云峰选择暂时退开，虽然避开了眼前冲突，却也错过了继续留在潘家园里遇见关键老人的机会，最后一次次退让，没有凑齐救命钱",
            bLabel = "当场硬刚，坚决不离开潘家园",
            bTitle = "硬刚",
            bDescription = "项云峰没有被吓退，而是硬着头皮留在潘家园继续周旋，正好把剧情推向遇见关键老人的主线方向。",
        ),
        64 to beipaiEndingChoice(
            episodeNumber = 64,
            triggerAt = 276.984,
            pauseAt = 277.454,
            question = "你现在弄丢了奶奶的四千块救命钱，走投无路之际，观察你很久的陌生前辈抛出了一周就能赚两万的邀约，你会怎么选？",
            aLabel = "答应王显生的邀约，跟着他入行快速凑钱救奶奶",
            aTitle = "入行",
            aDescription = "顺着原剧情推进，项云峰就此踏入盗墓行当，后续凭借过人的鉴宝能力成长为江湖上赫赫有名的“神眼锋”。",
            bLabel = "拒绝来路不明的高收益邀约，想其他合法途径凑救命钱",
            bTitle = "拒邀",
            bDescription = "彻底偏离原剧情，项云峰不会踏入盗墓行当，开启完全不同的人生发展路径。",
        ),
        66 to beipaiEndingChoice(
            episodeNumber = 66,
            triggerAt = 206.317,
            pauseAt = 206.619,
            question = "作为刚入行的北派新人项云峰，站在龙穴入口前的你会做出什么选择？",
            aLabel = "听从团队安排，跟着老成员依次有序进入龙穴",
            aTitle = "跟队",
            aDescription = "项云峰压住好奇心，听从把头和老成员的安排，排在队伍中间谨慎进入龙穴，探墓行动按原计划开启。",
            bLabel = "趁大家不注意率先独自钻进龙穴入口",
            bTitle = "抢先",
            bDescription = "项云峰独自闯入龙穴，踩中翻板机关，毒箭从墙缝射出，他惊险躲到石柱后，反而误打误撞摸到主墓室入口和第一件金器。",
        ),
        67 to beipaiEndingChoice(
            episodeNumber = 67,
            triggerAt = 360.984,
            pauseAt = 361.371,
            question = "你作为在场的新人学徒项云峰，闻到这股冲天的诡异恶臭之后，会做出什么选择？",
            aLabel = "听从把头王显生的指令，留下来和大家一起探查缸内的真相",
            aTitle = "探查",
            aDescription = "众人忍住恶臭，围住缸体，按把头指令一点点打开封口，墓穴里隐藏的恐怖秘密即将揭露。",
            bLabel = "立刻转身往墓穴出口方向跑，优先保住自己的性命",
            bTitle = "逃离",
            bDescription = "项云峰独自狂奔，撞开隐蔽侧门，意外撞见南派盗墓者留守成员，双方在墓道深处拔刀对峙。",
        ),
        69 to beipaiEndingChoice(
            episodeNumber = 69,
            triggerAt = 212.65,
            pauseAt = 213.019,
            question = "此刻你作为北派团伙的核心决策者，会做出什么选择？",
            aLabel = "遵循富贵险中求的行规，立刻下令开启墓门",
            aTitle = "开门",
            aDescription = "众人压下对南派盗墓者离奇死亡的疑虑，合力开启芥子行宫墓门，进入国家级大墓内部继续探索。",
            bLabel = "察觉墓门异常警示，立刻下令全队撤退返回地面",
            bTitle = "撤退",
            bDescription = "众人暂时放弃开门，封死盗洞并做隐蔽标记，准备摸清南派盗墓者死因后再回来，却在地面发现另一伙人的踪迹。",
        ),
        70 to beipaiEndingChoice(
            episodeNumber = 70,
            triggerAt = 101.317,
            pauseAt = 101.68,
            question = "眼看未知致命生物马上扑到人群面前，你作为核心成员项云峰当下要做出什么选择？",
            aLabel = "立刻转身跟着大部队往墓穴出口狂奔撤离",
            aTitle = "撤离",
            aDescription = "未知生物冲出后，项云峰跟随大部队边抵抗边撤向墓穴出口，主线进入逃生节奏。",
            bLabel = "抄起身边的洛阳铲冲上去，先挡住怪物给其他人争取反应时间",
            bTitle = "迎战",
            bDescription = "项云峰攥紧洛阳铲迎上怪物，侧身避开利爪后刺中怪物肩颈，给队友争取到反击时间。",
        ),
        81 to beipaiEndingChoice(
            episodeNumber = 81,
            triggerAt = 189.984,
            pauseAt = 190.32,
            question = "你作为盗墓团队的一员，此刻会做出什么选择？",
            aLabel = "服从把头的指令，先全员撤离从长计议",
            aTitle = "撤离",
            aDescription = "老三被众人强行拉住，团队先撤出青铜门前，从长计议安全破门方案。",
            bLabel = "支持老三立刻动手强行破拆青铜门救人",
            bTitle = "破门",
            bDescription = "老三把撬棍卡进青铜门缝，众人合力撬动自来石，门后传出二哥微弱的求救声。",
        ),
    )

    private val endingsByEpisode = mapOf(
        1 to endingChoice(
            episodeNumber = 1,
            triggerAt = 91.333,
            pauseAt = 91.787,
            question = "如果你站在唐颖的位置，此刻还会继续隐忍陆励和小黎吗？",
            aLabel = "维持表面平静，按原剧情推进",
            aTitle = "暗流未断",
            aDescription = "陆励选择继续敷衍与拖延，把见不得光的关系暂时压回水面下，婚姻裂痕却已经无法真正缝合。",
            bLabel = "现在就把关系挑明",
            bTitle = "当场摊牌",
            bDescription = "唐颖不再忍耐小黎的逼迫和陆励的敷衍，当场把这段见不得光的关系撕开，让体面彻底崩塌。",
        ),
        4 to endingChoice(
            episodeNumber = 4,
            triggerAt = 32.5,
            pauseAt = 32.954,
            question = "如果你站在唐颖的位置，此刻会先压住误会，还是当场说破？",
            aLabel = "维持表面平静，按原剧情推进",
            aTitle = "危险沉默",
            aDescription = "两人都选择先压下尴尬与暧昧，让越界边缘的情绪继续潜伏，等待下一次更危险的爆发。",
            bLabel = "现在就把关系挑明",
            bTitle = "界线撕裂",
            bDescription = "一句“像偷情”彻底戳破暧昧遮羞布，关系界线被公开拉开，谁也无法再装作无事发生。",
        ),
        9 to endingChoice(
            episodeNumber = 9,
            triggerAt = 266.65,
            pauseAt = 267.12,
            question = "如果你站在唐颖的位置，此刻会先解释清楚，还是直接转身离开？",
            aLabel = "先压下情绪，听完解释",
            aTitle = "忍住怀疑",
            aDescription = "面对陆励突然追到车旁的危局，唐颖先压住情绪，试图把眼前的误会和难堪延后处理。",
            bLabel = "立刻翻脸，不给解释机会",
            bTitle = "车窗之外",
            bDescription = "唐颖不愿再被陆励质问和误解，在局面最僵的时候直接转身离开，把解释和旧情一起丢在身后。",
        ),
        10 to endingChoice(
            episodeNumber = 10,
            triggerAt = 117.5,
            pauseAt = 117.954,
            question = "如果你站在唐颖的位置，此刻会冷静拒绝，还是当场反击？",
            aLabel = "按原剧情继续",
            aTitle = "冷面拒绝",
            aDescription = "唐颖保持清醒和克制，用干脆的拒绝切断纠缠，把主动权牢牢抓回自己手里。",
            bLabel = "做出相反选择",
            bTitle = "反手回击",
            bDescription = "唐颖不止是拒绝，而是顺势反击，让江辞云在众目睽睽下彻底失去体面。",
        ),
        12 to endingChoice(
            episodeNumber = 12,
            triggerAt = 87.984,
            pauseAt = 88.454,
            question = "如果你站在唐颖的位置，此刻会先忍下羞辱，还是立刻撕破脸？",
            aLabel = "维持表面平静，按原剧情推进",
            aTitle = "体面假象",
            aDescription = "面对陆励的绝情摊牌，唐颖暂时没有立刻掀桌，而是把屈辱压回心底，等待更完整的证据和反击时机。",
            bLabel = "现在就把关系挑明",
            bTitle = "婚约尽碎",
            bDescription = "被陆励羞辱到极点的唐颖选择正面撕破脸，把这段早已腐坏的婚姻直接推进不可回头的终局。",
        ),
        14 to endingChoice(
            episodeNumber = 14,
            triggerAt = 104.067,
            pauseAt = 104.454,
            question = "如果你站在唐颖的位置，此刻会含泪签字，还是等江辞云出手改局？",
            aLabel = "按原剧情继续",
            aTitle = "含泪落笔",
            aDescription = "为了救父亲，唐颖只能吞下委屈签下协议，把尊严和代价一起按进那张纸里。",
            bLabel = "做出相反选择",
            bTitle = "绝境截签",
            bDescription = "就在唐颖被逼到无路可退时，江辞云强势闯入阻断签字，让她从绝境边缘被硬生生拉回。",
        ),
        16 to endingChoice(
            episodeNumber = 16,
            triggerAt = 93.15,
            pauseAt = 93.62,
            question = "如果你站在唐颖的位置，此刻会先忍住，还是当众回击？",
            aLabel = "做出相反选择",
            aTitle = "沉默承压",
            aDescription = "面对当众羞辱和与陆励有关的恶意揣测，唐颖先把委屈压下，让风暴暂时停在失控前一秒。",
            bLabel = "按原剧情继续",
            bTitle = "当众打脸",
            bDescription = "唐颖不再做沉默承受者，而是直接回击，把挑衅者推上更难堪的高台。",
        ),
        18 to endingChoice(
            episodeNumber = 18,
            triggerAt = 141.65,
            pauseAt = 142.12,
            question = "如果你站在唐颖的位置，此刻会尝试相信江辞云，还是彻底封心？",
            aLabel = "先压下情绪，听完解释",
            aTitle = "试着相信",
            aDescription = "即使伤痕未愈，唐颖还是在江辞云的保护和真心面前留下一丝缝隙，没有彻底关上门。",
            bLabel = "立刻翻脸，不给解释机会",
            bTitle = "封心止步",
            bDescription = "唐颖把最后一点动摇也掐灭，选择拒绝所有保护与靠近，把自己重新封进坚硬外壳。",
        ),
        20 to endingChoice(
            episodeNumber = 20,
            triggerAt = 157.15,
            pauseAt = 157.62,
            question = "如果你站在唐颖的位置，此刻会接受江辞云的承诺，还是坚持自己扛下去？",
            aLabel = "按原剧情继续",
            aTitle = "求婚未答",
            aDescription = "江辞云的求婚和承诺像一道突然落下的光，唐颖没有立刻接受，却也没有马上转身离开。",
            bLabel = "做出相反选择",
            bTitle = "拒绝靠岸",
            bDescription = "即使江辞云愿意替她撑腰，唐颖仍决定不把未来交给新的依附，而是自己走出困局。",
        ),
        22 to endingChoice(
            episodeNumber = 22,
            triggerAt = 84.15,
            pauseAt = 84.62,
            question = "如果你站在江辞云的位置，此刻会先顶住家族安排，还是彻底公开决裂？",
            aLabel = "维持表面平静，按原剧情推进",
            aTitle = "拒婚示威",
            aDescription = "江辞云先用强硬表态顶住家族安排，把不属于自己的婚约推回原处。",
            bLabel = "现在就把关系挑明",
            bTitle = "家门决裂",
            bDescription = "他不再只是反抗，而是把冲突彻底公开化，用最决绝的方式切断被安排的人生轨迹。",
        ),
        25 to endingChoice(
            episodeNumber = 25,
            triggerAt = 40.817,
            pauseAt = 41.287,
            question = "如果你站在唐颖的位置，此刻会回望旧情，还是彻底离开陆励？",
            aLabel = "先压下情绪，听完解释",
            aTitle = "心碎回望",
            aDescription = "唐颖仍旧回望那段曾经深信不疑的婚姻，在废墟前承认自己所有付出都已被陆励彻底背叛。",
            bLabel = "立刻翻脸，不给解释机会",
            bTitle = "远走高飞",
            bDescription = "当最后一点留恋也被伤透，唐颖终于选择转身，把和陆励有关的旧日幻梦一并抛在身后。",
        ),
    )
}
