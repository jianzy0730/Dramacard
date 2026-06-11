package com.dramacard.client.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DramaCardColors = darkColorScheme(
    primary = Color(0xFFFFD56C),
    onPrimary = Color(0xFF241600),
    secondary = Color(0xFF9E88FF),
    background = Color(0xFF09101D),
    surface = Color(0xFF121B2F),
    onSurface = Color(0xFFF5F1E8),
)

@Composable
fun DramaCardTheme(
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = DramaCardColors,
        content = content,
    )
}
